import http from "k6/http";
import { sleep } from "k6";


export let options = {
vus: 50,
duration: "30s",
};


export default function () {
http.post("http://localhost:8000/v1/messages", JSON.stringify({
conversation_id: "k6test",
sender_id: "tester",
recipient_ids: ["tg_1"],
content: "hello"
}), {
headers: { "Content-Type": "application/json" }
});
sleep(1);
}