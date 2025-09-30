import json
import re

from docint_app.services.ollama_client_service import get_ollama_client


class VideoTopicModellingService:
    def __init__(self, transcription: str):
        self.client = get_ollama_client()
        self.model = "llama3.3:latest"
        self.transcription = transcription

    def _split_sentences(self, text: str):
        raw = re.split(r'(?<=[.!?])\s+(?=[A-Z(""Oo0])', text.strip())
        sentences = [s.strip() for s in raw if s.strip()]
        return list(enumerate(sentences))

    def _assemble_segments(self, sentences, segments_json): # type: ignore[no-untyped-def]
        idx_to_sent = {i: s for i, s in sentences}
        out = []
        for seg in segments_json["segments"]:
            chunk = " ".join(idx_to_sent[i] for i in range(seg["start_idx"], seg["end_idx"] + 1))
            out.append({"title": seg["title"], "video_chunk": chunk})
        return {"segments": out}

    def _chunk_with_ollama_ranges(self, sentences): # type: ignore[no-untyped-def]
        system = (
            "You are an expert lecture segmenter.\n"
            "Task: Split the lecture into topic-based segments using the provided sentence list.\n"
            "CRITICAL RULES:\n"
            "1) Output ONLY JSON in the exact shape: {\"segments\": [{\"title\": string, \"start_idx\": int, \"end_idx\": int}, ...]}.\n"
            "2) Use ONLY the sentence indices I give you. Do not invent text.\n"
            "3) Segments must be contiguous, non-overlapping, and fully cover ALL sentences from 0 to N-1 exactly once.\n"
            "4) start_idx <= end_idx for each segment.\n"
            "5) Segments should be <= 7 sentences while remaining on a single topic.\n"
            "6) Choose concise titles.\n"
            "Do NOT define functions, tools, or schemas. No prose. No markdown."
        )

        example = {
            "segments": [
                {"title": "Introduction", "start_idx": 0, "end_idx": 4},
                {"title": "While loops", "start_idx": 5, "end_idx": 11}
            ]
        }

        preview = "\n".join(f"[{i}] {s}" for i, s in sentences)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "EXAMPLE FORMAT:\n" + json.dumps(example, ensure_ascii=False)},
            {"role": "user", "content": "SENTENCES (index → sentence):\n" + preview + "\n\nReturn ONLY the JSON object now."}
        ]

        response = self.client.chat(
            model=self.model,
            messages=messages,
            stream=False,
            format="json",
            options={"temperature": 0, "seed": 42, "raw": True}
        )

        return response['message']['content']

    def extract_topics(self): # type: ignore[no-untyped-def]
        sentences = self._split_sentences(self.transcription)
        raw = self._chunk_with_ollama_ranges(sentences)
        parsed = json.loads(raw)
        final = self._assemble_segments(sentences, parsed) # dict with "segments" key and list of {title, video_chunk} vals
        return final["segments"] # list of {title, video_chunk} dicts

def get_video_topic_modelling_service(transcription: str) -> VideoTopicModellingService:
    return VideoTopicModellingService(transcription)