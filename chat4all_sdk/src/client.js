import axios from "axios";
import { retry } from "./utils.js";
import { UploadManager } from "./uploader.js";


export class Chat4AllClient {
constructor(baseUrl, token) {
this.baseUrl = baseUrl.replace(/\/$/, "");
this.token = token;
this.upload = new UploadManager(this);


this.http = axios.create({
baseURL: this.baseUrl,
headers: { Authorization: `Bearer ${this.token}` },
});
}


async sendMessage({ conversationId, senderId, recipients, content, messageId }) {
messageId = messageId || crypto.randomUUID();


return retry(async () => {
const r = await this.http.post("/v1/messages", {
conversation_id: conversationId,
sender_id: senderId,
recipient_ids: recipients,
content,
message_id: messageId,
});
return r.data;
});
}
}