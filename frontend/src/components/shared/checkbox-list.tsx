import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

export type CheckboxListItem = {
  value: string;
  label: string;
  hint?: string | null;
};

type CheckboxListProps = {
  items: CheckboxListItem[];
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  emptyMessage?: string;
  className?: string;
};

export function CheckboxList({
  items,
  value,
  onChange,
  disabled = false,
  emptyMessage = "Nothing to choose from.",
  className,
}: CheckboxListProps) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  function toggle(item: string) {
    onChange(
      value.includes(item)
        ? value.filter((entry) => entry !== item)
        : [...value, item],
    );
  }

  return (
    <div
      className={cn(
        "max-h-64 space-y-2 overflow-y-auto rounded-md border p-3",
        className,
      )}
    >
      {items.map((item) => (
        <div key={item.value} className="flex items-start gap-2">
          <Checkbox
            className="mt-0.5"
            checked={value.includes(item.value)}
            onCheckedChange={() => toggle(item.value)}
            disabled={disabled}
          />

          <span
            className="cursor-pointer text-sm select-none"
            onClick={() => {
              if (!disabled) {
                toggle(item.value);
              }
            }}
          >
            <span className="font-medium">{item.label}</span>

            {item.hint ? (
              <span className="block text-xs text-muted-foreground">
                {item.hint}
              </span>
            ) : null}
          </span>
        </div>
      ))}
    </div>
  );
}
