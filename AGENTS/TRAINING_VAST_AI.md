# AgroResilience — train Qwen3.5-4B on Vast.ai RTX 4090

> Archived optional local-model runbook as of 2026-11-14. DeepSeek API is the primary direction; this training workflow is not a production prerequisite. Revisit only if a local provider is selected later. See [MODEL_PROVIDER.md](MODEL_PROVIDER.md).

Updated: 2026-11-14. This is a pre-production training runbook, not an executed or GPU-tested job. No instance has been rented and no money has been spent by the agent.

## 1. Deployment decision

- Training: rent **one RTX 4090, 24 GB VRAM**, on [Vast.ai](https://vast.ai/).
- Base model: **Qwen/Qwen3.5-4B**, the post-trained model, not `4B-Base`.
- Method: supervised fine-tuning with **bf16 LoRA**, initially text-only.
- Local inference: **RTX 3050, 6 GB VRAM**, using a separately validated quantized export.
- Train and evaluate before production. There is **no production training loop**, automatic weight update, or `training=1` branch in the serving orchestrator.
- Future updates repeat this offline workflow and produce a separately versioned candidate. The production model changes only after evaluation and deliberate promotion.

Unsloth's model-specific guide lists approximately 10 GB for its 4B bf16 LoRA setup; 24 GB gives headroom, but long sequences and other settings can still cause out-of-memory errors. The guide discourages Qwen3.5 4-bit QLoRA, so do not use that as the starting training recipe. [Qwen3.5 training guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune)

Quantizing **after** bf16 training for local inference is distinct from doing QLoRA training.

## 2. Prepare the dataset before paying for a GPU

Sources:

- `AGENTS/AgroResilience_Farmer_Questionnaire.md`: adopted intake requirements, optional fields, and refinements.
- `AGENTS/LOCAL_MODEL.md`: conversation behavior and tool/resource boundaries.
- `AGENTS/AgroResilience_Technical_Scientific_Specification_v1.1.docx.md`: scientific limits and deterministic analytics.
- User-provided datasets and reviewed agent-generated examples.

Train behavior: concise interviewing, structured information extraction, corrections, uncertainty, asking for sufficient evidence, and explaining approved tool results. Do not try to memorize every future farmer's field data or replace scientific scripts with model guesses.

### Dataset requirements

1. English only initially.
2. Use supervised conversations with the correct answer already supplied. Raw Markdown/Excel documents are source material, not automatically useful SFT examples.
3. Start with a proposed 1,000–3,000 diverse, reviewed examples; this is a starting experiment, not a quality guarantee. Use a small subset for the smoke test.
4. Preserve separate train/validation/test splits, for example 80/10/10, grouped by farmer, field and scenario family. Keep related synthetic variants in the same split.
5. Remove identifying information. Real farmer conversations require their separate optional training permission.
6. Validate numerical/scientific examples against approved scripts or reviewed evidence. A second agent's agreement alone is not scientific verification.
7. Include explicit unknowns, contradictions, corrections, multiple fields, unavailable tools/data, unsupported files, and malicious instructions inside uploaded content.
8. Examples should not promise recommendations in the conversational MVP. No invented yields, erosion values, profit guarantees, or precise sunflower intervals without calendar years.
9. For tool calling, use the **actual server tool schemas and outputs**. Until those are available, run a conversational behavior pilot only; do not invent production function names/contracts.
10. Keep long-history retrieval, evidence grounding and both response modes in held-out evaluation. A model trained only on short direct answers has not demonstrated preserved thinking ability.

Store a manifest alongside the dataset: version, source/license, reviewer, consent eligibility where applicable, split strategy, creation date, and hashes. Keep metadata outside the model's conversation text.

### JSONL format

Prepare `train.jsonl`, `validation.jsonl`, and `test.jsonl`. Each line is one JSON object with a `messages` list. Use the selected model's own chat template through the trainer; do not manually paste ChatML delimiters or switch to another model's template.

These four examples illustrate formatting only. They are **not a complete training set**:

```jsonl
{"messages":[{"role":"system","content":"You are AgroResilience. Ask concise questions, preserve unknowns, and never invent field facts."},{"role":"user","content":"My field is 30 hectares, and I do not know its soil texture."},{"role":"assistant","content":"Saved the area as 30 ha and soil texture as unknown. Where is the field located?"}]}
{"messages":[{"role":"system","content":"Field A currently has a recorded area of 30 ha. Acknowledge clear corrections briefly."},{"role":"user","content":"Field A is 35 hectares, not 30."},{"role":"assistant","content":"Updated Field A’s area to 35 ha."}]}
{"messages":[{"role":"system","content":"The farmer has Field A and Field B. Clarify ambiguous updates."},{"role":"user","content":"Change the area to 35 hectares."},{"role":"assistant","content":"Which field should I update: Field A or Field B?"}]}
{"messages":[{"role":"system","content":"No usable soil measurements or analysis results are available. Do not invent results."},{"role":"user","content":"Tell me my exact soil erosion rate."},{"role":"assistant","content":"I cannot calculate an erosion rate from the available information. Can you provide the field location and any soil or erosion-analysis data you have?"}]}
```

The saved/updated wording above represents turns **after a successful state write**. In tool-training traces, include the corresponding real successful tool result; do not teach the model to claim a write succeeded before the server commits it.

Validate the files locally before rental:

```python
# Save as validate_dataset.py beside the three JSONL files; run with Python 3.
import hashlib
import json
from pathlib import Path

seen = {}
for split in ("train", "validation", "test"):
    path = Path(f"{split}.jsonl")
    count = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        messages = row.get("messages")
        assert isinstance(messages, list) and messages, (split, number)
        for message in messages:
            assert message.get("role") in {"system", "user", "assistant", "tool"}, (split, number)
            assert isinstance(message.get("content"), str), (split, number)
        assert messages[-1]["role"] == "assistant", (split, number)
        digest = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
        assert digest not in seen, ("Duplicate conversation", split, number, seen.get(digest))
        seen[digest] = (split, number)
        count += 1
    assert count, f"Empty split: {split}"
    print(split, count, hashlib.sha256(path.read_bytes()).hexdigest())
```

This checks basic text-message structure and exact duplicates only. It does not validate scientific correctness, consent, near-duplicate leakage, field provenance, or real tool-call schemas. Add those reviews before training on tool traces.

## 3. Rent the instance yourself

In Vast.ai:

1. Register, verify the account, add credit, and add your SSH public key.
2. Filter offers for **1 × RTX 4090 with 24 GB**, with adequate reliability/availability. Prefer on-demand for the first run to avoid interruption complications.
3. Recommended host allocation: at least 4 CPU cores, 32 GB system RAM, and **100 GB disk** for caches, adapters, merged weights and exports. These are runbook starting allocations, not platform minimums.
4. Select a current **PyTorch/Linux template with SSH access** and a compatible NVIDIA driver. Record its image/tag or digest. The selected disk allocation cannot simply be expanded later.
5. Inspect the actual hourly, storage and transfer charges before selecting Rent. Prices depend on the offer; this guide does not quote a live rate.
6. Copy the instance's SSH command from the dashboard.

Follow the [Vast.ai quickstart](https://docs.vast.ai/guides/get-started/quickstart). Vast instances already run in containers; do not attempt Docker-in-Docker. Use the selected environment directly. [Instance FAQ](https://github.com/vast-ai/docs/blob/main/guides/reference/faq/instances.mdx)

## 4. Connect and check the GPU

The following local commands use Bash. Replace the example values with those from your instance's SSH panel; the port may differ from 22, and proxy hostnames are valid.

```bash
VAST_SSH_PORT=12345
VAST_SSH_HOST=replace-with-your-vast-ssh-host
VAST_SSH_USER=root
ssh -p "$VAST_SSH_PORT" "$VAST_SSH_USER@$VAST_SSH_HOST"
```

Inside the rented instance:

```bash
nvidia-smi
python --version
python -c 'import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.is_bf16_supported())'
mkdir -p /workspace/agro-training/data /workspace/agro-training/artifacts
```

Expect a 4090 with roughly 24 GB, CUDA available, and bf16 support. If the GPU is missing or the environment is incompatible, correct the instance/template before downloading the model. Use Python 3.11–3.13 for the documented Unsloth environment. [Installation requirements](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)

## 5. Install and open Unsloth Studio

Use the official installer in this disposable rented environment. Download it first so you can inspect it:

```bash
cd /workspace/agro-training
curl -fsSL https://unsloth.ai/install.sh -o install-unsloth.sh
less install-unsloth.sh
sh install-unsloth.sh
```

Follow installer prompts. If instructed to reopen the shell, reconnect, then check:

```bash
command -v unsloth
unsloth studio --help
```

Run Studio in the persistent terminal/tmux session supplied by the instance:

```bash
unsloth studio -H 127.0.0.1 -p 8888
```

If 8888 is occupied by the template's Jupyter service, select a free port in both this command and the tunnel below. Keep the process running.

On your **local PC**, in another terminal, set the same SSH variables and open a tunnel:

```bash
ssh -N -p "$VAST_SSH_PORT" -L 127.0.0.1:18888:127.0.0.1:8888 "$VAST_SSH_USER@$VAST_SSH_HOST"
```

Open `http://127.0.0.1:18888` and complete Studio's first-run account setup. This requires no Cloudflare connection or public Studio port. The official guides describe the [Studio training workflow](https://unsloth.ai/docs/models/qwen3.5/fine-tune) and [Vast SSH forwarding](https://docs.vast.ai/guides/instances/connect/ssh).

Transfer your reviewed files from your PC; run where `data/` contains the three JSONL files and manifest:

```bash
scp -P "$VAST_SSH_PORT" data/train.jsonl data/validation.jsonl data/test.jsonl data/manifest.json "$VAST_SSH_USER@$VAST_SSH_HOST:/workspace/agro-training/data/"
```

Alternatively upload through Studio's file picker. Keep a local copy regardless.

## 6. Configure a pilot training run

In Studio, select **Qwen/Qwen3.5-4B**, supervised fine-tuning, and local conversational data. Map the `messages` field and inspect rendered examples before starting. Use the model's existing template. Do not use a random example dataset supplied by a tutorial.

These are **proposed starting hyperparameters**, not an optimized production configuration:

| Setting | Starting value |
| --- | --- |
| Training method | LoRA, bf16/16-bit base; disable 4-bit loading |
| Scope | Language layers only; freeze vision components |
| Sequence length | 2,048 tokens |
| Per-device batch | 1 |
| Gradient accumulation | 4 (effective batch 4 on one GPU) |
| LoRA rank / alpha / dropout | 16 / 16 / 0 |
| Target | Supported attention + MLP linear layers; leave embeddings/head frozen |
| Learning rate | 0.0001 |
| Weight decay | 0.01 |
| Warm-up | 5% of optimizer steps |
| Scheduler / seed | Linear / 3407 |
| Gradient checkpointing | Enabled |
| Packing | Off for the first compatibility run |
| Logging / checkpoint | Every 10 / 50 optimizer steps; retain 2 checkpoints initially |
| Pilot length | Maximum 50–100 optimizer steps, using training split only |
| First full run | 1 epoch; consider a second only after validation |

The choices are a conservative application-specific starting point informed by [LoRA configuration guidance](https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide). Field labels may vary with Studio versions. Save/export the actual configuration. Do not silently use a 4-bit preset or a larger model if a UI option differs.

Important checks:

- Provide validation separately; never add test examples to training. If the installed Studio cannot use an explicit validation split, evaluate separately outside training and retain the test set untouched.
- Inspect tokenized lengths. Split/review oversized examples instead of truncating off their supervised answer. Increase sequence length only after measuring memory.
- Prefer assistant-response-only loss when the chosen trainer/template supports it correctly. Inspect actual non-masked target tokens on a sample; an all-masked target is invalid. Do not apply a Llama-specific response-mask template to Qwen.
- Keep first-run focus on interviewing/extraction, then test both thinking and fast modes. Final-answer-only SFT does not by itself establish preserved reasoning ability.
- Record environment versions and the exact downloaded base-model revision. Do not update dependencies halfway through a run. From the shell/environment used by Studio, save `python -m pip freeze > /workspace/agro-training/artifacts/environment.txt`; also copy the base-model revision and exported Studio configuration into the release bundle.

If a release does not expose the needed controls, use its official [Qwen3.5-4B notebook](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision.ipynb) as a reference for supported APIs, adapting the data/scope deliberately. It is a vision notebook: do not run its example vision dataset and assume it trained your text assistant. Resume only after the rendered data and selected scope are correct.

## 7. Benchmark first; calculate time and cost

Do not assume inference tokens/second equal training tokens/second.

After kernel compilation/warm-up, measure the time between two known optimizer steps. With effective batch 4 and un-packed data:

```text
steps_per_epoch ≈ ceil(number_of_training_examples / 4)
training_seconds ≈ remaining_optimizer_steps × measured_seconds_per_optimizer_step
```

Packing or a changed batch size changes this calculation. Add evaluation, checkpoint/export, setup and data transfer time.

Another useful estimate is:

```text
processed_tokens = examples × average_tokens_per_example × epochs
training_seconds = processed_tokens / measured_training_tokens_per_second
```

Illustration **only**, with 512 tokens/example, 2 epochs and two hypothetical throughputs. These are not RTX 4090 benchmark claims:

| Training examples | Processed tokens | At 100 training tokens/s | At 500 training tokens/s |
| --- | --- | --- | --- |
| 1,000 | 1,024,000 | 2 h 51 min | 34 min |
| 5,000 | 5,120,000 | 14 h 13 min | 2 h 51 min |
| 10,000 | 10,240,000 | 28 h 27 min | 5 h 41 min |

Use the pilot to replace these assumed rates. The epoch count is illustrative, not a requirement. Longer traces, poor packing, padding and evaluation overhead can change elapsed time substantially. Start the real run from a clean base+adapter initialization rather than accidentally adding a full run on top of pilot training.

```text
estimated_cost = billable_hours × actual_offer_hourly_rate + storage + transfer
```

Record a budget limit before the full run. Recheck the running instance and balance rather than leaving an unattended continuous training loop.

## 8. Evaluate before export and again after quantization

Compare the base model and candidate on the same held-out prompts/tool fixtures, not only training loss:

- Correct extraction, explicit unknowns, required-field follow-ups and field selection.
- Latest correction wins; old jobs/history cannot overwrite current values.
- No claims of successful saving without a successful state tool result.
- Concise acknowledgements and helpful evidence-gap questions.
- Approved tool names/arguments only; never arbitrary code execution or code modification.
- Relevant history retrieval without cross-user leakage.
- No fabricated scientific values or premature recommendations.
- Unsupported-file notices and problem/support responses.
- Both fast and thinking modes terminate and produce coherent final answers.

Hard failures such as invented field measurements, unauthorized tools or cross-user data access block release even if average accuracy improves. Define numeric task thresholds against your base-model baseline before selecting the winning run; do not invent a “95% confidence” from a model score.

Evaluate your model and orchestration separately. Fine-tuning cannot implement database transactions, account ownership, queuing or stale-write protection; those remain server responsibilities.

## 9. Save and export

From Studio, export and preserve:

1. LoRA adapter and configuration.
2. Tokenizer/processor files and chat template.
3. Base model ID/revision and merged 16-bit weights if practical.
4. Training configuration, dataset hashes, dependency versions, logs and evaluation results.
5. Final quantized GGUF candidate.

Export a **Q4_K_M GGUF candidate** initially for the 6 GB inference budget. Keep the higher-precision source so you can try a different quantization without retraining. Test the export; file size alone does not establish loaded memory usage or quality.

For code-based Unsloth exports, its documented interface includes:

```python
# Run only inside the training environment with the trained model/tokenizer loaded.
model.save_pretrained_gguf("/workspace/agro-training/artifacts/agro-qwen35-4b", tokenizer, quantization_method="q4_k_m")
```

Prefer the Studio export screen if using this runbook's UI workflow. A LoRA adapter alone is not a standalone GGUF. Preserve the exact template and end-of-sequence behavior when changing runtimes. [GGUF export documentation](https://unsloth.ai/docs/basics/inference-and-deployment/saving-to-gguf.md)

Copy final outputs into `/workspace/agro-training/artifacts/` before download. In particular, if Studio saved into another directory, copy those files there or download them through Studio; do not assume that this runbook directory automatically contains Studio's internal checkpoints.

## 10. Download and test on the RTX 3050

From your local PC:

```bash
mkdir -p agro-training-results
scp -r -P "$VAST_SSH_PORT" "$VAST_SSH_USER@$VAST_SSH_HOST:/workspace/agro-training/artifacts" ./agro-training-results/
```

Verify file checksums on both ends. Do not destroy the instance until the adapter, template, final export and manifest are safely downloaded.

One local testing route is current **Ollama with Qwen3.5 support**. Rename/copy the actual exported GGUF to `agro-qwen35-4b-q4_k_m.gguf` in a local model directory. Beside it create `Modelfile`:

```text
FROM ./agro-qwen35-4b-q4_k_m.gguf
PARAMETER num_ctx 4096
```

Then run locally:

```bash
ollama create agroresilience-qwen35-4b-v1 -f Modelfile
ollama run agroresilience-qwen35-4b-v1
```

Ollama imports already-quantized GGUF; it does not quantize GGUF during import. [Ollama import guide](https://docs.ollama.com/import)

This is a local smoke test, not backend integration. Preserve/test the Qwen template and thinking setting. The context length 4096 is a starting test value, not the final service setting. Confirm the entire model's GPU placement with runtime diagnostics and inspect `nvidia-smi`; CPU offloading can hide a memory shortfall while increasing latency.

Test one response first, then the two simultaneous active runs required by `LOCAL_MODEL.md`, including context and output limits. Measure first-writing latency, output throughput, peak VRAM and quality. The rented GPU's training speed says nothing about RTX 3050 serving speed. Do not deploy if two runs OOM or miss agreed targets; adjust context/output budgets and retest explicitly.

## 11. End the rental and retain a release bundle

After verifying the download, end the instance from the Vast dashboard. **Stopping preserves instance storage and its charges; deleting/destroying the instance removes its container data.** Any separately retained volumes/storage must also be reviewed if no longer needed. [Vast instance management](https://github.com/vast-ai/docs/blob/main/guides/instances/manage-instances.mdx)

Retain a local release directory containing:

```text
release-v1/
  adapter/
  tokenizer-and-template/
  agro-qwen35-4b-q4_k_m.gguf
  training-config.json
  dataset-manifest.json
  environment.txt
  evaluation-results.json
  checksums.txt
```

Only then promote a versioned artifact to production. Keep the previous serving artifact available for rollback. Production has no trainer, optimizer, dataset-generation agents or automatic weight updates.

## 12. If something fails

| Problem | Action |
| --- | --- |
| GPU out of memory | Keep batch 1; reduce sequence length, check gradient checkpointing and that vision/full fine-tuning are off. Close other GPU jobs. Do not change to a different model silently. |
| Invalid/empty loss or no target tokens | Inspect dataset mapping, tokenization and response masking before continuing. |
| Repetition or broken output after export | Check chat template, special tokens and runtime compatibility; compare the higher-precision candidate. |
| Better loss but worse corrections/tools | Reject the candidate; inspect data and evaluation leakage. |
| Session disconnect | Reconnect to the instance's persistent terminal/tmux. A disconnect is not proof training stopped. |
| Instance failure/interruption | Resume only from a complete checkpoint with the same base/data/config; adapter-only saves do not necessarily contain optimizer/scheduler state. |
| Unsupported upload/parser | Reject that type clearly; do not train the assistant to claim it read unsupported content. |

No remote GPU run has been executed as part of writing this guide. Installation, UI behavior, training fit and export must be verified on the selected rental before a full paid run.
