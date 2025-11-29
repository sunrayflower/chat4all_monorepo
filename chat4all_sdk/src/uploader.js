import axios from "axios";
import fs from "fs";
import FormData from "form-data";
import { retry } from "./utils.js";


export class UploadManager {
constructor(client) {
this.client = client;
}


async initUpload(ownerId, filename) {
const r = await this.client.http.post(
`/v1/uploads/init?owner_id=${ownerId}&filename=${filename}`
);
return r.data;
}


async uploadFile(ownerId, filepath) {
const meta = await this.initUpload(ownerId, filepath.split("/").pop());
const { url, fields } = meta.presigned_fields;


const buffer = fs.readFileSync(filepath);
const form = new FormData();
for (const k in fields) form.append(k, fields[k]);
form.append("file", buffer);


await retry(() => axios.post(url, form, { headers: form.getHeaders() }));
return { ok: true, object_key: meta.object_key };
}
}