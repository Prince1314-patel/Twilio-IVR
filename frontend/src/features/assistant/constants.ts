import type { PromptAction } from "@/features/assistant/types";

export const PROMPT_ACTIONS: PromptAction[] = [
  {
    id: "book",
    label: "Book Appointment",
    prompt: "I want to book a new appointment.",
    description: "Start a new appointment booking flow.",
  },
  {
    id: "reschedule",
    label: "Reschedule",
    prompt: "I need to reschedule my appointment.",
    description: "Change an existing appointment date or time.",
  },
  {
    id: "cancel",
    label: "Cancel Appointment",
    prompt: "Please cancel my appointment.",
    description: "Cancel an upcoming appointment.",
  },
  {
    id: "status",
    label: "Check Status",
    prompt: "Show my upcoming appointments.",
    description: "Review appointments already scheduled.",
  },
];

