# 24. Fully local AI phone agent for a small office (state as of 2026-11-20)

Scope: answer calls, book appointments, take messages, transfer to a human, with local speech and language models. Each fact carries its source. Anything not checked in this pass is marked UNVERIFIED. Vendor and marketing figures are labelled as such.

## 1. Telephony

**Asterisk.** The current LTS is **Asterisk 24.0.0**, released 5 November 2026 per the GitHub releases page (https://github.com/asterisk/asterisk/releases) and the Asterisk downloads page, which labels 24.0.0 "Latest LTS Version" (https://www.asterisk.org/downloads/). Asterisk 22 LTS remains supported. Asterisk 23 is the standard (non-LTS) release. The Asterisk 20 standard branch reached end of bug support in October 2026 (https://www.asteriskservice.com/blog/asterisk-20-end-of-life/, secondary). Support windows for 24 were not checked against the official lifecycle page (UNVERIFIED).

**FreeSWITCH.** The open-source release line is at **1.11.x**. The 1.11.3 release (28 August 2026) is the fix for CVE-2026-116779, an unauthenticated SIP MESSAGE flaw that could run API and OS commands; affected versions are everything through 1.11.2 (https://www.hitcommunications.com/en-us/blog/freeswitch-cve-2026-116779-sip-rce-exploited, secondary; cross-check with https://www.tenable.com/cve/CVE-2026-116779). A 1.11.4 release is reported on the FusionPBX forum (https://www.pbxforums.com/threads/freeswitch-1-11-4.9357/post-37874), but its date is UNVERIFIED. The FreeSWITCH Enterprise line is 20.26.2, dated 21 May 2026 (https://developer.signalwire.com/freeswitch/reference/release-notes-enterprise/). Also note a second RTP source-validation CVE, CVE-2026-119292, fixed in 1.11.2 (https://mallory.ai/vulnerabilities/CVE-2026-119292, secondary). Whichever PBX you pick, expose SIP only through the trunk provider's IP allowlist, not to the internet.

**Connecting office numbers to a local server.** Two common patterns, neither sourced in this pass (UNVERIFIED):
- *SIP trunk:* a cloud SIP provider holds the DID numbers and sends INVITEs to your Asterisk over a static IP with registration or IP auth. This is the usual choice for a small office.
- *Analog or VoIP gateway:* an FXO/FXS gateway (or a DAHDI card) connects copper lines (POTS) to the server. Analog lines need no provider SIP, but you pay per line and lose the cheap DID pool.

**How audio reaches the agent.** Three paths are documented:
- **AudioSocket.** Asterisk's own protocol definition is at https://docs.asterisk.org/Configuration/Channel-Drivers/AudioSocket/. It is invoked from the dialplan as `AudioSocket(uuid,host:port)` or via ARI external media, and Asterisk opens a TCP stream to your service. Practitioner write-ups call it "deliberately small" (https://www.ictcontact.com/asterisk-audiosocket-vs-chan-websocket-ai-voice-agent/, secondary; that page was not readable on re-fetch, the snippet is from search).
- **ARI external media / chan_websocket.** Asterisk's `chan_websocket` moves call audio over WebSockets, and a practitioner recommendation is to prefer it on Asterisk 20.18, 22.8 or newer (https://ictinnovations.com/asterisk-ai-voice-agent-lessons-audiosocket-barge-in/, secondary, snippet only). One Dograh community thread reports user-to-agent audio not flowing with chan_websocket external media while AudioSocket worked (https://github.com/orgs/dograh-hq/discussions/307, secondary). Test both on your exact Asterisk build.
- **WebRTC.** Asterisk 22 is reported to have better WebRTC handling (https://www.innovateasterisk.com/asterisk-22-ubuntu-24-04-install-guide-2026/, secondary). WebRTC is the path for browser callers, not PSTN calls, so for a phone line it matters less.

**Voice-agent frameworks that run on local models.**
- **Pipecat** (BSD-2-clause, Python). Its docs say the local defaults for evals are Kokoro for TTS and Moonshine or Whisper for STT, and it supports local or HTTP-hosted services (https://docs.pipecat.ai/pipecat/evals/overview). The repository describes it as an open-source framework for real-time voice and multimodal agents (https://github.com/pipecat-ai/pipecat). Pipecat 1.0 is listed in its docs. Licence wording was not read directly (UNVERIFIED).
- **LiveKit Agents** (Apache-2.0 framework). The turn detection models are under the separate **LiveKit Model License** (https://github.com/livekit/agents). Its turn detector is an ONNX/Transformers model (https://huggingface.co/livekit/turn-detector). LiveKit is built around WebRTC rooms, so a PSTN call must be bridged into a room through SIP.
- **Vocode** was not checked in this pass (UNVERIFIED).

What each needs: a Python host, a GPU or CPU for the STT, LLM and TTS services, and a transport. Pipecat is the simplest fit for an Asterisk box because you can wire AudioSocket or a WebSocket transport straight into the pipeline.

## 2. Speech to text (local)

- **Whisper large-v3-turbo** (OpenAI, **MIT**, 99 languages): https://huggingface.co/openai/whisper-large-v3-turbo. Benchmark (faster-whisper's own table, for the older large-v2 model, 13 minutes of audio, GPU): faster-whisper fp16 beam 5 takes 1m03s at 4525 MB VRAM; int8 takes 59 s at 2926 MB; batch size 8 with int8 takes 16 s at 4500 MB (https://github.com/SYSTRAN/faster-whisper, Benchmark section, fetched). Whisper is batch-oriented; streaming needs chunked decoding around it. A CPU test reported by a vendor blog gives turbo under 20 s versus 143 s for large-v3 on CPU, hardware unstated (https://tesseraai.cloud/en/blog/whisper-large-v3-turbo-vs-large-v3-cpu-eu/, secondary, not verified).
- **faster-whisper** (CTranslate2, MIT): the usual local server. **whisper.cpp** runs on CPU and Apple Silicon, and its own benchmark table in the faster-whisper README shows a 1m05s run at fp16 with flash attention (https://github.com/SYSTRAN/faster-whisper).
- **NVIDIA Parakeet TDT 0.6B v3**: 600M-parameter FastConformer-TDT, 25 European languages with automatic language detection, punctuation and capitalisation included, **CC-BY-4.0**, released 14 August 2025 (https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3). The model card says it is optimised for NVIDIA GPUs and points to the NeMo docs. Its WER chart is an image; the numbers were not extracted. Secondary reports say it is more accurate than turbo on English and much faster on NVIDIA GPUs (https://www.arunbaby.com/speech-tech/0073-whisper-vs-parakeet-asr-decision/, secondary). A secondary comparison gives an RTFx of 3,333 for Parakeet against 462 for another model on the Open ASR Leaderboard (https://www.orcarouter.ai/blog/nemotron-3-5-transcribe-vs-nvidia-parakeet-tdt-0-6b, secondary, UNVERIFIED against the leaderboard itself). NVIDIA's Speech NIM documents streaming ASR benchmarks that include Parakeet TDT 0.6B v3 (https://docs.nvidia.com/nim/speech/latest/reference/performances/asr/performance.html); the table was not extracted, so streaming latency is UNVERIFIED.
- **Canary** and **Qwen3-ASR 1.7B** were named in a broadcast-model comparison (https://amiralabs.com/blog/whisper-parakeet-canary-qwen3-asr-broadcast-model-selection, secondary). Their licences and figures were not checked.

Hardware: turbo and Parakeet both fit comfortably on an 8 GB consumer NVIDIA card (the faster-whisper table shows 2.9 to 6 GB at large-v2 size). Parakeet is the stronger pick only if the office is English or one of the 25 European languages and you have NVIDIA hardware. Whisper turbo covers the other 74 languages.

## 3. Text to speech (local)

- **Kokoro-82M** (**Apache-2.0**, 82M parameters): "comparable quality to larger models while being significantly faster," per its model card (https://huggingface.co/hexgrad/Kokoro-82M). It is the default in Pipecat's local examples (see section 1). It is English-focused on the card. Voice quality is good for IVR-style prompts; it is not the most natural option.
- **Piper**: the original `rhasspy/piper` repository was **archived on 6 October 2025** and is read-only; development moved to `OHF-Voice/piper1-gpl`, licensed **GPL-3.0-or-later** (https://github.com/rhasspy/piper, and the successor's licence per https://www.promptquorum.com/power-local-llm/piper-tts-review, secondary). The GPL matters if you ship a combined binary. Piper is fast on CPU, which makes it a good fallback on a box with no GPU.
- **Qwen3-TTS** (Alibaba Qwen team, released January 2026): an open-source series "supporting stable, expressive, and streaming" synthesis (https://github.com/QwenLM/Qwen3-TTS; the technical report at https://arxiv.org/html/2601.15621v1 describes a 12 Hz tokenizer that emits the first packet early). The **97 ms latency** figure appears only on marketing sites (https://qwen3-tts.org/, https://qwen3ttsai.com/) and is UNVERIFIED. The licence is reported as Apache 2.0 by a secondary source (https://www.bland.ai/blog/open-source-tts-vs-hosted-api); the GitHub README licence section was not extracted (UNVERIFIED primary).
- **Chatterbox** (Resemble AI, MIT licence). **Status changed:** Resemble's GitHub page says "As of August 2026, Chatterbox is retired research and is no longer maintained" (https://github.com/resemble-ai/chatterbox, via search snippet). Do not pick it for new work. The Bland blog reports that Resemble stopped selling TTS to new customers on 13 August 2026 (https://www.bland.ai/blog/resemble-ai-review, secondary, a competitor).
- **Orpheus** (Canopy Labs, Llama-3B-based speech LM, Apache 2.0): named as Apache 2.0 by Modal's comparison (https://modal.com/blog/open-source-tts) and Bland's (https://www.bland.ai/blog/open-source-tts-compared). It is a larger model than Kokoro, so expect more GPU and more time to first audio. Latency figures were not verified.

Recommendation for a phone agent: Kokoro for the default voice (small, Apache-2.0, fast), with Qwen3-TTS as the candidate upgrade once its latency is measured on your hardware.

## 4. Voice activity detection and turn-taking

- **Silero VAD** (the usual frame-level speech detector): the snakers4 repository was reachable only as a navigation page, so its licence and figures are UNVERIFIED in this pass.
- **Pipecat Smart Turn v3.x** (**BSD-2-clause**): a semantic turn detector that reads the raw waveform rather than the transcript. Backbone is a **Whisper Tiny encoder** with a linear head, **8M parameters**, an 8 MB int8 ONNX checkpoint (https://huggingface.co/pipecat-ai/smart-turn-v3). Pipecat's blog title claims CPU inference in about 12 ms (https://www.daily.co/blog/announcing-smart-turn-v3-with-cpu-inference-in-just-12ms/, secondary, not re-read). v3.1 and v3.2 followed; v3.2 is described as 40% better on short utterances (https://www.daily.co/blog/smart-turn-v3-2-handling-noisy-environments-and-short-responses/, vendor blog).
- **LiveKit turn detector**: an audio-plus-text end-of-turn model with an ONNX build, 14 languages, under the LiveKit Model License (https://huggingface.co/livekit/turn-detector, https://docs.livekit.io/agents/logic/turns/turn-detector/).
- **Barge-in**: requires that the VAD run on the caller's audio while TTS is playing, with echo cancellation on the Asterisk side. The practitioner write-up "Building an Asterisk AI Voice Agent" lists barge-in as a lesson from AudioSocket work (https://ictinnovations.com/asterisk-ai-voice-agent-lessons-audiosocket-barge-in/, secondary, snippet only). Test it with a real handset, not only a loopback.

## 5. End-to-end latency budgets

No primary benchmark for a full local phone stack was found. Practitioner figures:
- A vendor blog's three-service budget: streaming STT about 250 ms, LLM time to first token about 200 ms, TTS first chunk about 150 ms, which sums to roughly 600 ms "on paper" before transport (https://www.bland.ai/blog/lowest-latency-voice-ai, secondary, a competitor).
- A Hacker News post reports about 400 ms from the caller stopping to the first syllable, with full STT, LLM and TTS in the loop (https://news.ycombinator.com/item?id=47224295, single practitioner, UNVERIFIED).
- A Medium write-up titled "Engineering a sub-500 ms voice agent" (https://medium.com/data-science-collective/engineering-a-sub-500-ms-voice-agent-where-every-millisecond-goes-d3fb6bbc610d) could not be read (blocked); its figures are UNVERIFIED.

What it implies for model size: a sub-600 ms budget needs an STT that returns a final transcript within a few hundred milliseconds of end-of-speech, an LLM with a time to first token near 200 ms (a small local instruct model on GPU, not a 70B), and a TTS that starts on the first sentence. Kokoro at 82M and turbo-class Whisper are inside that budget on a single consumer GPU. Larger LLMs push the total past one second; the phone line will feel slow. The SIP trunk and PSTN add their own delay, which these numbers exclude.

## 6. What cannot be local

- **The carrier or SIP trunk.** Dial tone, DIDs, PSTN termination and number porting are the provider's. Local software cannot replace them.
- **Emergency calling.** The FCC requires interconnected VoIP providers to supply E911: automatic 911 service as a mandatory feature, a customer may not opt out, the provider must collect the registered physical location before activation, and must send the callback number and location to the emergency call centre (https://www.fcc.gov/consumers/guides/voip-and-911-service). A local AI agent does not satisfy that. Keep a provider with E911 on the trunk, and do not route 911 through the agent (a practical rule, not a sourced one).
- **Call recording consent.** Recording rules depend on the state. The Digital Media Law Project reports that 38 states and DC have one-party consent laws (https://www.dmlp.org/legal-guide/recording-phone-calls-and-conversations; page not re-read on fetch, the figure is from search). Some states require all parties to consent (https://www.justia.com/50-state-surveys/recording-phone-calls-and-conversations/). Federal wiretap law (18 U.S.C. 2511, https://www.law.cornell.edu/uscode/text/18/2511) is the baseline; the one-party exception text in subsection (2)(d) was not extracted in this pass (UNVERIFIED). This is not legal advice. Put a recording notice in the greeting and check your state's rule for each caller area code.
- **Outbound robocalls.** The FCC's February 2024 Declaratory Ruling says AI-generated voices count as "artificial" under the TCPA, so calls that use them need prior express consent (https://www.fcc.gov/document/fcc-makes-ai-generated-voices-robocalls-illegal and https://www.fcc.gov/document/fcc-confirms-tcpa-applies-ai-technologies-generate-human-voices). The FCC's consumer guide repeats that AI-generated voice calls require consumer consent unless an exemption applies (https://www.fcc.gov/consumers/guides/robocalls-rules-callers). An office agent that only answers inbound calls and transfers to humans is outside that rule; an agent that places outbound appointment reminders is inside it.

## 7. Memory needs specific to calls

Not sourced in this pass; these are design recommendations, not verified findings.
- **Caller identification:** a lookup table keyed on E.164-normalised caller ID, with a fallback for withheld numbers. Caller ID is spoofable, so use it only to greet, never to authorise a change.
- **Per-call working memory:** a short state object for the live call (intent, slots being filled, last confirmed date). Discard or summarise it when the call ends.
- **Post-call summary and facts:** write one summary and a small set of structured facts (name, callback, appointment, message) to the office database after each call, with a link to the transcript.
- **Transcripts as an event log:** append each turn (speaker, timestamp, text, confidence) to an append-only table. Keep it separate from the facts, so a mistaken fact can be corrected without losing the record.

## Recommended minimal stack (as of 2026-11-20)

| Layer | Component | Licence | Why |
|---|---|---|---|
| PBX | Asterisk 24 LTS (or 22 LTS if 24 packages are not yet in your distro) | GPL-2.0 (UNVERIFIED in this pass) | Current LTS (24.0.0, 5 Nov 2026) |
| Trunk | SIP trunk with E911 and IP allowlist | Commercial | Carrier duties stay with the provider |
| Media path | AudioSocket first; chan_websocket if your Asterisk build passes a live test | As Asterisk | Both documented; test on your build |
| Framework | Pipecat | BSD-2-clause | Local defaults documented, transports for Asterisk streams |
| VAD and turn | Silero VAD (UNVERIFIED licence) plus Smart Turn v3.2 | BSD-2-clause (Smart Turn) | Small, CPU-capable |
| STT | faster-whisper with large-v3-turbo on an NVIDIA GPU | MIT | Broadest language coverage; Parakeet TDT 0.6B v3 if English or EU languages only |
| TTS | Kokoro-82M | Apache-2.0 | Small and fast; Piper as CPU fallback (GPL-3.0, note the licence) |
| LLM | Local instruct model, size chosen to meet the TTFT budget | Per model | Not researched in this pass (UNVERIFIED) |

Do not use Chatterbox (retired August 2026). Confirm FreeSWITCH or Asterisk patch level before exposing SIP.

## Sources

- Asterisk releases: https://github.com/asterisk/asterisk/releases
- Asterisk downloads: https://www.asterisk.org/downloads/
- Asterisk 20 end of life (secondary): https://www.asteriskservice.com/blog/asterisk-20-end-of-life/
- AudioSocket protocol: https://docs.asterisk.org/Configuration/Channel-Drivers/AudioSocket/
- FreeSWITCH Enterprise release notes: https://developer.signalwire.com/freeswitch/reference/release-notes-enterprise/
- FreeSWITCH release notes index: https://developer.signalwire.com/freeswitch/reference/release-notes/
- CVE-2026-116779 (Tenable): https://www.tenable.com/cve/CVE-2026-116779
- CVE-2026-119292 (secondary): https://mallory.ai/vulnerabilities/CVE-2026-119292
- Pipecat repository: https://github.com/pipecat-ai/pipecat
- Pipecat evals docs: https://docs.pipecat.ai/pipecat/evals/overview
- LiveKit Agents: https://github.com/livekit/agents
- LiveKit turn detector (model card): https://huggingface.co/livekit/turn-detector
- LiveKit turn detector docs: https://docs.livekit.io/agents/logic/turns/turn-detector/
- Whisper large-v3-turbo: https://huggingface.co/openai/whisper-large-v3-turbo
- faster-whisper benchmark: https://github.com/SYSTRAN/faster-whisper
- Parakeet TDT 0.6B v3: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3
- NVIDIA Speech NIM ASR performance: https://docs.nvidia.com/nim/speech/latest/reference/performances/asr/performance.html
- Kokoro-82M: https://huggingface.co/hexgrad/Kokoro-82M
- Piper (archived): https://github.com/rhasspy/piper
- Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS
- Qwen3-TTS technical report: https://arxiv.org/html/2601.15621v1
- Chatterbox: https://github.com/resemble-ai/chatterbox
- Smart Turn v3 (model card): https://huggingface.co/pipecat-ai/smart-turn-v3
- Smart Turn repository: https://github.com/pipecat-ai/smart-turn
- FCC VoIP and 911: https://www.fcc.gov/consumers/guides/voip-and-911-service
- FCC AI-generated voices ruling: https://www.fcc.gov/document/fcc-makes-ai-generated-voices-robocalls-illegal
- FCC TCPA and AI: https://www.fcc.gov/document/fcc-confirms-tcpa-applies-ai-technologies-generate-human-voices
- FCC robocall rules for callers: https://www.fcc.gov/consumers/guides/robocalls-rules-callers
- 18 U.S.C. 2511: https://www.law.cornell.edu/uscode/text/18/2511
- Digital Media Law Project, recording calls: https://www.dmlp.org/legal-guide/recording-phone-calls-and-conversations
- Justia 50-state survey, recording calls: https://www.justia.com/50-state-surveys/recording-phone-calls-and-conversations/
- Secondary, vendor or competitor blogs (figures not independently verified): https://www.bland.ai/blog/open-source-tts-compared, https://www.bland.ai/blog/lowest-latency-voice-ai, https://www.bland.ai/blog/resemble-ai-review, https://www.tesseraai.cloud/en/blog/whisper-large-v3-turbo-vs-large-v3-cpu-eu/, https://www.daily.co/blog/smart-turn-v3-2-handling-noisy-environments-and-short-responses/, https://www.orcarouter.ai/blog/nemotron-3-5-transcribe-vs-nvidia-parakeet-tdt-0-6b
- Practitioner notes: https://www.hitcommunications.com/en-us/blog/freeswitch-cve-2026-116779-sip-rce-exploited, https://ictinnovations.com/asterisk-ai-voice-agent-lessons-audiosocket-barge-in/, https://github.com/orgs/dograh-hq/discussions/307, https://news.ycombinator.com/item?id=47224295
