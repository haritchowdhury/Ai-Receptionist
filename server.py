from flask import Flask, render_template, jsonify, request
from flask_apscheduler import APScheduler
from dbDrivers.session_operations import SessionOperations
import json
import os
import hashlib
from datetime import datetime, timezone
from dotenv import load_dotenv
from upstash_vector import Index
from sentence_transformers import SentenceTransformer

app = Flask(__name__)
scheduler = APScheduler()
db = SessionOperations()

# Load environment variables
load_dotenv()

# Initialize embedding model and vector client globally
embedding_model = None
vector_client = None

def initialize_vector_components():
    """Initialize embedding model and vector client"""
    global embedding_model, vector_client

    try:
        # Initialize embedding model
        if embedding_model is None:
            embedding_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
            print("SUCCESS: Embedding model loaded")

        # Initialize Upstash Vector client
        if vector_client is None:
            if not os.getenv("UPSTASH_VECTOR_REST_URL") or not os.getenv("UPSTASH_VECTOR_REST_TOKEN"):
                print("WARNING: Missing Upstash environment variables - vector ingestion disabled")
                return False

            vector_client = Index(
                url=os.getenv("UPSTASH_VECTOR_REST_URL"),
                token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
            )
            print("SUCCESS: Connected to Upstash Vector database")

        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize vector components: {e}")
        return False

def create_vector_id(text):
    """Create a unique ID for each text"""
    return hashlib.md5(text.encode()).hexdigest()

def ingest_qa_to_vector_db(question, answer, session_id):
    """Ingest question-answer pair into vector database"""
    if not initialize_vector_components():
        print("WARNING: Vector database components not available - skipping ingestion")
        return False

    try:
        namespace = os.getenv("NAMESPACE")
        if not namespace:
            print("WARNING: Missing NAMESPACE environment variable - skipping vector ingestion")
            return False

        # Combine question and answer for better context
        qa_content = f"Q: {question}\nA: {answer}"

        # Get embedding
        embedding = embedding_model.encode([qa_content]).tolist()[0]

        # Create vector data
        vector_id = create_vector_id(qa_content)
        vector_data = {
            "id": vector_id,
            "vector": embedding,
            "metadata": {
                'title': f"Q&A - Session {session_id}",
                'category': 'Customer_QA',
                'question': question,
                'answer': answer,
                'session_id': session_id,
                'content': qa_content
            },
            "data": qa_content
        }

        # Upsert to vector database
        response = vector_client.upsert(
            vectors=[vector_data],
            namespace=namespace
        )

        print(f"SUCCESS: Q&A ingested to vector database for session {session_id}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to ingest Q&A to vector database: {e}")
        return False

@scheduler.task('interval', id='periodic_task', seconds=1)
def scheduled_job():
    print("runs every second")
    """Task that runs every second"""
    try:
        current_time = datetime.now(timezone.utc)
        pending_sessions = db.get_all_member_sessions("PENDING")
        updated_count = 0
        for session in pending_sessions:
            # Parse the created_at timestamp
            created_at_str = session.get('created_at')
            if not created_at_str:
                continue
            try:
                # Parse the timestamp and make it timezone-aware (UTC)
                created_at = datetime.fromisoformat(created_at_str).replace(tzinfo=timezone.utc)

                # Calculate time difference
                time_diff = current_time - created_at

                # If more than 60 seconds old, mark as UNRESOLVED
                if time_diff.total_seconds() > 60:
                    session_id = session.get('session_id')
                    if session_id:
                        success = db.update_member_session(session_id, "UNRESOLVED")
                        if success:
                            updated_count += 1
                            print(f"Marked session {session_id} as UNRESOLVED (age: {time_diff.total_seconds():.1f}s)")

            except (ValueError, TypeError) as e:
                print(f"Error parsing timestamp for session {session.get('session_id', 'unknown')}: {e}")
                continue

        if updated_count > 0:
            print(f"Updated {updated_count} sessions to UNRESOLVED at {current_time}")

    except Exception as e:
        print(f"ERROR in scheduled_job: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/member-sessions')
def get_member_sessions():
    try:
        sessions = db.get_all_member_sessions()
        print(sessions)
        return jsonify(sessions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resolve-session', methods=['POST'])
def resolve_session():
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        session_id = data.get('session_id')
        answer = data.get('answer')

        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400

        if not answer or not answer.strip():
            return jsonify({'error': 'answer is required'}), 400

        # First, get the current session to retrieve the question
        try:
            sessions = db.get_all_member_sessions()
            current_session = None
            for session in sessions:
                if session['session_id'] == session_id:
                    current_session = session
                    break

            if not current_session:
                return jsonify({'error': 'Session not found'}), 404

            question = current_session.get('question', '')

        except Exception as e:
            print(f"ERROR: Failed to retrieve session data: {e}")
            return jsonify({'error': 'Failed to retrieve session data'}), 500

        # Update the session with resolved status and answer
        success = db.update_member_session(session_id, "RESOLVED", answer=answer.strip())

        if success:
            # Append Q&A to salon_data.txt
            if question and question.strip():
                try:
                    with open("IngestSalonData/salon_data.txt", "a", encoding="utf-8") as f:
                        f.write(f"\nQ: {question.strip()}\nA: {answer.strip()}\n")
                    print(f"SUCCESS: Q&A for session {session_id} appended to salon_data.txt")
                except Exception as e:
                    print(f"WARNING: Failed to append Q&A to salon_data.txt: {e}")

            # Ingest Q&A into vector database
            if question and question.strip():
                vector_success = ingest_qa_to_vector_db(question.strip(), answer.strip(), session_id)
                if vector_success:
                    print(f"SUCCESS: Q&A for session {session_id} ingested into vector database")
                else:
                    print(f"WARNING: Failed to ingest Q&A for session {session_id} into vector database")

            return jsonify({'message': 'Session resolved successfully'})
        else:
            return jsonify({'error': 'Session not found or could not be updated'}), 404

    except Exception as e:
        print(f"ERROR: Exception in resolve_session: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    scheduler.init_app(app)
    scheduler.start()
    app.run(debug=True, host='0.0.0.0', port=5000)