import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { CheckboxList } from "@/components/shared/checkbox-list";
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
import { useCreateUser } from "@/features/users/use-users";
import { apiErrorMessage } from "@/lib/api-error";
import type { Role } from "@/types/role";

const schema = z.object({
  email: z.email("Enter a valid email address"),
  full_name: z.string().min(1, "Full name is required").max(255, "Too long"),
  password: z
    .string()
    .min(8, "Use at least 8 characters")
    .max(128, "Too long"),
  roles: z.array(z.string()),
});

type FormValues = z.infer<typeof schema>;

type CreateUserDialogProps = {
  roles: Role[];
  onOpenChange: (open: boolean) => void;
};

export function CreateUserDialog({
  roles,
  onOpenChange,
}: CreateUserDialogProps) {
  const createUser = useCreateUser();

  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      roles: [],
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await createUser.mutateAsync(values);
      toast.success("User created");
      onOpenChange(false);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not create the user"));
    }
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New user</DialogTitle>

          <DialogDescription>
            Create a sign-in account and choose what it can access.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          <div className="space-y-2">
            <Label htmlFor="new-user-email">Email</Label>

            <Input
              id="new-user-email"
              type="email"
              autoComplete="off"
              disabled={isSubmitting}
              aria-invalid={errors.email ? true : undefined}
              {...register("email")}
            />

            {errors.email ? (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-user-name">Full name</Label>

            <Input
              id="new-user-name"
              autoComplete="off"
              disabled={isSubmitting}
              aria-invalid={errors.full_name ? true : undefined}
              {...register("full_name")}
            />

            {errors.full_name ? (
              <p className="text-sm text-destructive">
                {errors.full_name.message}
              </p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-user-password">Temporary password</Label>

            <Input
              id="new-user-password"
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
            <Label>Roles</Label>

            <Controller
              control={control}
              name="roles"
              render={({ field }) => (
                <CheckboxList
                  items={roles.map((role) => ({
                    value: role.name,
                    label: role.name,
                    hint: role.description,
                  }))}
                  value={field.value}
                  onChange={field.onChange}
                  disabled={isSubmitting}
                  emptyMessage="No roles exist yet. Create one on the Roles screen."
                />
              )}
            />
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
              {isSubmitting ? "Creating..." : "Create user"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
