# Work/Home cutover checklist

1. Keep v6 production uploader running until v7 server health check passes.
2. Deploy v7 API + worker.
3. Install v7 client beside v6 on Work PC.
4. Configure Work token; do not store MySQL credentials in v7 client.
5. Test API status.
6. Use one small known spreadsheet to validate the end-to-end path.
7. Confirm MySQL batch, Phase2C, Phase3, Quick Check and AppSheet output.
8. Stop v6 uploader before the first real v7 production batch.
9. Install/configure v7 client on Home PC with a separate token.
10. Keep only one active production ingest path. The API rejects a new batch while another API batch is actively uploading/processing.
