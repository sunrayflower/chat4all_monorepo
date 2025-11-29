import WebSocket from "ws";


export class WSClient {
constructor(baseUrl, userId) {
this.url = baseUrl.replace("http", "ws") + `/v1/ws/${userId}`;
}


connect(onMessage) {
this.ws = new WebSocket(this.url);
this.ws.on("message", (msg) => onMessage(msg.toString()));
}


close() {
this.ws?.close();
}
}