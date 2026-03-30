import type { Submission } from "@prisma/client";

type FounderStatusSource = Pick<Submission, "status" | "adminNotes" | "reportUrl">;

export function founderStatusMessage(submission: FounderStatusSource): string {
  const note = submission.adminNotes.trim();

  if (note.startsWith("Daily analysis limit reached")) {
    return "Your submission is saved and will be processed when capacity becomes available.";
  }

  if (note.startsWith("Analysis needs more info")) {
    return "We need a bit more information before we can generate a reliable report.";
  }

  if (note.startsWith("Retry ")) {
    return "We hit a temporary issue and are retrying your analysis automatically.";
  }

  if (
    note.startsWith("Analysis failed after") ||
    note.startsWith("Automated analysis failed")
  ) {
    return "We hit a processing issue. The submission is saved and can be reviewed manually.";
  }

  if (note.startsWith("Resumed after server restart")) {
    return "Your submission resumed automatically after a restart and is back in the queue.";
  }

  if (submission.status === "reviewing") {
    return "Analysis is in progress.";
  }

  if (submission.status === "queued") {
    return "Your submission is queued for analysis.";
  }

  if (submission.status === "report_sent" && submission.reportUrl) {
    return "Your report is ready.";
  }

  return "";
}
