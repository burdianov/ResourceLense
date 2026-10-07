import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useResetUserPassword } from "@/features/users/use-users";
import { apiErrorMessage } from "@/lib/api-error";
import type { UserSummary } from "@/types/user";

const schema = z
  .object({
    password: z
      .string()
      .min(8, "Use at least 8 characters")
      .max(128, "Too long"),
    confirm: z.string(),
  })
  .refine((values) => values.password === values.confirm, {
    path: ["confirm"],
    message: "Passwords do not match",
  });

type FormValues = z.infer<typeof schema>;

type ResetPasswordDialogProps = {
  user: UserSummary;
  onOpenChange: (open: boolean) => void;
};

export function ResetPasswordDialog({
  user,
  onOpenChange,
}: ResetPasswordDialogProps) {
  const resetPassword = useResetUserPassword();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      password: "",
      confirm: "",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await resetPassword.mutateAsync({
        userId: user.id,
        password: values.password,
      });

      toast.success(`Password reset for ${user.email}`);
      onOpenChange(false);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not reset the password"));
    }
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Reset password</DialogTitle>

          <DialogDescription>
            Set a new password for {user.email}. Any session they have open
            will be signed out.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          <div className="space-y-2">
            <Label htmlFor="reset-password">New password</Label>

            <Input
              id="reset-password"
              type="password"
              autoComplete="new-password"
              disabled={isSubmitting}
              aria-invalid={errors.password ? true : undefined}
              {...register("password")}
            />

            {errors.password ? (
              <p className="text-sm text-destructive">
                {errors.password.message}
              </p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="reset-password-confirm">Confirm password</Label>

            <Input
              id="reset-password-confirm"
              type="password"
              autoComplete="new-password"
              disabled={isSubmitting}
              aria-invalid={errors.confirm ? true : undefined}
              {...register("confirm")}
            />

            {errors.confirm ? (
              <p className="text-sm text-destructive">
                {errors.confirm.message}
              </p>
            ) : null}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>

            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Resetting..." : "Reset password"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
