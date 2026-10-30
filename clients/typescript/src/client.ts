import { sessionBus, type ProxyInterface } from "@jellybrick/dbus-next";

// D-Bus configuration
const SERVICE_NAME = "org.lolacap.Service";
const OBJECT_PATH = "/org/lolacap/Service";
const INTERFACE_NAME = "org.lolacap.Service1";

// TypeScript representation of our Python D-Bus interface
interface LolacapInterface extends ProxyInterface {
  ListLanguages(): Promise<Record<string, string>>;

  StartJob(
    videoPath: string,
    language: string,
    softcoded: boolean,
  ): Promise<string>;

  GetJob(jobId: string): Promise<[string, number, string, string]>;
}

async function main(): Promise<void> {
  const bus = sessionBus();

  try {
    // Get the remote D-Bus object
    const object = await bus.getProxyObject(SERVICE_NAME, OBJECT_PATH);

    // Get our service interface
    const api = object.getInterface<LolacapInterface>(INTERFACE_NAME);

    // Call ListLanguages()
    const languages = await api.ListLanguages();

    console.log("Available languages:");

    for (const [code, name] of Object.entries(languages)) {
      console.log(`  ${code}: ${name}`);
    }

    // Start a processing job
    console.log("\nStarting video processing...");

    const jobId = await api.StartJob("video.mp4", "fon", false);

    console.log("Job started!");
    console.log("Job ID:", jobId);

    // Monitor job progress
    while (true) {
      const [status, progress, output, error] = await api.GetJob(jobId);

      console.log(`Status: ${status} | Progress: ${progress}%`);

      if (status === "done") {
        console.log("Job completed!");
        console.log("Output:", output);
        break;
      }

      if (status === "failed") {
        console.error("Job failed:", error);
        break;
      }

      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  } catch (error) {
    console.error("D-Bus error:", error);
    process.exitCode = 1;
  } finally {
    bus.disconnect();
  }
}

main();
