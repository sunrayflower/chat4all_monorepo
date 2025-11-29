from locust import HttpUser, task, between
import uuid


class ChatUser(HttpUser):
wait_time = between(1, 3)


@task
def send_message(self):
self.client.post("/v1/messages", json={
"conversation_id": "loadtest",
"sender_id": "tester",
"recipient_ids": ["tg_1"],
"content": f"hello {uuid.uuid4()}"
})