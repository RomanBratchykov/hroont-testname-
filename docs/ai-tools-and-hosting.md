# AI tool compatibility and free hosting audit

Checked 15 November 2026. This is an audit and hosting recommendation, not a deployment.

## AI compatibility

The model receives four JSON-schema function tools: read_history, get_capabilities, search_agronomy_knowledge and query_crop_soil_db. The server checks allowlisted names and validates arguments before invocation. Results have bounded sizes, explicit failures and source information. Both native Ollama and hosted DeepSeek provider paths have mocked wire tests. A direct invocation of the live document-search tool returned Kherson evidence. The 19 focused provider/tool regressions passed in this audit; no paid inference call was made.

RAG ingestion is an operational CLI and is not exposed to arbitrary model execution. No NASA retrieval, climate-feature, rotation-optimization, RUSLE or shared-profile-write tools are registered. Consequently AI can retrieve evidence, but it cannot yet execute the entire scientific pipeline or persist conversational profile corrections. Each such stage needs its deterministic implementation, validated input/output contract and allowlisted tool registration.

## Hosting fit

The current stack requires a persistent application database, PostgreSQL, Qdrant, a CPU embedding model, the Python API and the built frontend. The local virtual environment occupies approximately 1.8 GB of disk; that is not a measured RAM requirement. Existing databases occupy approximately 110 MB on disk. A VM with several GB of RAM and persistent storage is the practical target when inference uses DeepSeek externally.

| Provider | Assessment for the current full stack |
|---|---|
| Oracle Always Free A1 | Strongest candidate: current allowance is 2 OCPUs/12 GB RAM with 200 GB total block-volume quota. Capacity can be unavailable and idle instances can be reclaimed. This is ARM hardware; rebuild dependencies/use compatible images, not this laptop’s x86 binaries. |
| Render Free | Local files are ephemeral; services sleep after 15 idle minutes. Free persistent disks are unavailable and free PostgreSQL expires after 30 days. Requires substantial storage redesign. |
| Koyeb Free | 512 MB RAM/0.1 vCPU/2 GB disk, no persistent volumes, idle scale-to-zero. Insufficient for the combined local stack. |
| Hugging Face Spaces | CPU Basic has no hourly charge, but current policy requires a paid plan to create Docker/Gradio compute Spaces. Not a zero-cost new deployment of this server. |

Official sources:

- Oracle resources: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Oracle sign-up/card verification: https://www.oracle.com/cloud/free/faq/
- Render: https://render.com/docs/free
- Koyeb: https://www.koyeb.com/docs/reference/instances
- Hugging Face: https://huggingface.co/docs/hub/spaces-overview

Recommendation: provision an Always Free-eligible Ubuntu ARM VM for the DeepSeek-backed stack, subject to account eligibility/capacity. Oracle requires card verification. Keep the application and databases persistent, retain backups, configure the public origin and reverse proxy/tunnel, and verify ARM wheels/images before migration. Hosted inference still incurs DeepSeek API charges. No account, VM or public deployment was created by this audit.
