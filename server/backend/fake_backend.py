
import time


class FakeBackend:

    def process(
        self,
        video_path: str,
        language: str,
        softcoded: bool,
        progress_callback=None,
        cancel_event=None
    ) -> str:
        """
        Simulate video transcription and subtitling.

        progress_callback reports processing progress.
        """

        print(f"Processing video: {video_path}")
        print(f"Target language: {language}")
        print(f"Softcoded: {softcoded}")

        if progress_callback:
            progress_callback(25)

        for _ in range(20):
            self._check_cancellation(cancel_event)
            time.sleep(0.1)

        if progress_callback:
            progress_callback(60)

        for _ in range(20):
            self._check_cancellation(cancel_event)
            time.sleep(0.1)

        if progress_callback:
            progress_callback(90)

        self._check_cancellation(cancel_event)

        output_path = "fake_output.srt"

        subtitles = """1
                    00:00:01,000 --> 00:00:04,000
                    Hello from Lolacap!

                    2
                    00:00:05,000 --> 00:00:08,000
                    This is a fake subtitle.
                    """

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(subtitles)

        return output_path

    def _check_cancellation(self, cancel_event):
        if cancel_event and cancel_event.is_set():
            raise InterruptedError("Job cancelled")
