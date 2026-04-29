import pika
import json
import sys
import os

# 1. Environment  configuration - Reads from docker-compose.yml
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://admin:admin123@rabbitmq:5672/")

# Import your actual prediction function from model.py
# (Changed from 'from app.model' to 'from model' for Docker)
from model import predict

def callback(ch, method, properties, body):
    """This function runs automatically every time a new message arrives."""
    try:
        data = json.loads(body)
        image_id = data.get("image_id")
        image_path = data.get("image_path")
        
        print(f" [▼] Received task for Image ID: {image_id}")
        print(" [⧗] Starting deep learning inference...")

        # Run the AI model
        results = predict(image_path) 
        
        # Build the payload with the result data
        result_payload = {
            "status":            "RESULT_READY",
            "image_id":          image_id,
            "diagnosis":         results.get("diagnosis",           "Unknown"),
            "confidence":        results.get("confidence_pct",      0.0),  
            "stone_coverage":    results.get("stone_coverage_pct",  0.0),   
            "severity":          results.get("severity",            "N/A"),
            "result_image_path": results.get("result_image_path",   "N/A") 
        }

        # Send the final results back to the notification queue
        ch.basic_publish(
            exchange='',
            routing_key='notifications_queue',
            body=json.dumps(result_payload),
            properties=pika.BasicProperties(delivery_mode=2) # make message persistent
        )
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f" [▲] Finished and notified system for Image ID: {image_id}")
        print(f" [📸] Visual result saved at: {results.get('result_image_path')}\n")

    except Exception as e:
        print(f" [!] Error processing image: {e}")
        # nack the message so it doesn't get stuck, but don't requeue if it's a code error
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    print(f" [*] Connecting to RabbitMQ broker...")
    
    # Use URLParameters to handle the full connection string from environment variables
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    
    channel = connection.channel()
    
    # Ensure both queues exist
    channel.queue_declare(queue='analysis_queue', durable=True)
    channel.queue_declare(queue='notifications_queue', durable=True)
    
    # Process only one image at a time (Fair dispatch)
    channel.basic_qos(prefetch_count=1) 
    channel.basic_consume(queue='analysis_queue', on_message_callback=callback)

    print(' [*] Worker is alive and listening to "analysis_queue". To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)