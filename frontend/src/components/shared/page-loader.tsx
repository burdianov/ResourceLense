import { LoaderCircle } from "lucide-react";

export function PageLoader() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center">
      <LoaderCircle className="size-6 animate-spin text-muted-foreground" />
      <span className="sr-only">Loading</span>
    </div>
  );
}
