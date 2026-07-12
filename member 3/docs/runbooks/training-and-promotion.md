# Training, Promotion, and Rollback

Prepare and validate reviewed data before installing the heavyweight `.[training]` group. Replace all
base/tokenizer placeholders with verified immutable revisions and hashes, then run training preflight.
Training output is an experiment until held-out quality/safety, latency/memory, three-run stability,
Member 1 loader, Member 2 atomic activation, independent-Critic, and rollback gates pass.

Never train from GGUF. Train the compatible Hugging Face base, retain PEFT separately, and use the
official llama.cpp `convert_lora_to_gguf.py`. If the adapter loses, keep the base active and preserve the
negative result. Rollback changes only Member 2's atomic active pointer to the verified predecessor;
Member 1 must demonstrate loader compatibility before live use.
