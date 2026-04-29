from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil, os, uuid, pika, json
from model import predict

app = FastAPI(title="Medical AI Scanner Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve result mask images over HTTP
os.makedirs("/app/results", exist_ok=True)
app.mount("/results", StaticFiles(directory="/app/results"), name="results")

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://admin:admin123@rabbitmq:5672/")

# ── Health check ──
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ai_service", "model": "EfficientNet-B0 + UNet++"}

# ── Main analyze endpoint — called directly by patient_service ──
@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    # Save uploaded file to temp location
    tmp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Run your real PyTorch model
        result = predict(tmp_path, seg_threshold=0.60)

        # Save mask result image if it exists
        mask_url = None
        if result.get("result_image_path") and os.path.exists(result["result_image_path"]):
            fname = os.path.basename(result["result_image_path"])
            dest  = f"/app/results/{fname}"
            shutil.move(result["result_image_path"], dest)
            mask_url = f"/results/{fname}"

        return {
            "filename":           file.filename,
            "diagnosis":          result["diagnosis"],
            "confidence_pct":     result["confidence_pct"],
            "ai_result":          result["diagnosis"],
            "ai_confidence":      result["confidence_pct"],
            "all_probabilities":  result["all_probabilities"],
            "stone_coverage_pct": result["stone_coverage_pct"],
            "severity":           result["severity"],
            "mask_image_url":     mask_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ── Async endpoint — called by RabbitMQ worker (F-09) ──
@app.post("/api/analyze-async")
async def analyze_async(file: UploadFile = File(...), image_id: int = 0):
    """
    Saves the file and publishes a job to RabbitMQ analysis_queue.
    Returns immediately without waiting for AI result.
    """
    save_path = f"/app/results/{image_id}_{file.filename}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        params     = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel    = connection.channel()
        channel.queue_declare(queue="analysis_queue",     durable=True)
        channel.queue_declare(queue="notifications_queue",durable=True)

        message = json.dumps({
            "image_id":   image_id,
            "image_path": save_path
        })
        channel.basic_publish(
            exchange="",
            routing_key="analysis_queue",
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()

        return {
            "status":   "queued",
            "image_id": image_id,
            "message":  "Analysis job sent to queue. Result will be ready shortly."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue error: {str(e)}")