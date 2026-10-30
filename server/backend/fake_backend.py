import time


class FakeBackend:

    def process(self, video_path: str, language: str, softcoded: bool) -> str:
        """
        Simulate video transcription and subtitling.

        Returns the path to a fake SRT subtitle file.
        """

        print(f"Processing video: {video_path}")
        print(f"Target language: {language}")
        print(f"Softcoded: {softcoded}")

        time.sleep(5)

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