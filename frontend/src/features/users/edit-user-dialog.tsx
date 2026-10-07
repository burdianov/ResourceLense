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
import { Switch } from "@/components/ui/switch";
import { useUpdateUser } from "@/features/users/use-users";
import { apiErrorMessage } from "@/lib/api-error";
import type { Role } from "@/types/role";
import type { UserSummary } from "@/types/user";

const schema = z.object({
  full_name: z.string().min(1, "Full name is required").max(255, "Too long"),
  roles: z.array(z.string()),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

type EditUserDialogProps = {
  user: UserSummary;
  roles: Role[];
  isSelf: boolean;
  onOpenChange: (open: boolean) => void;
};

export function EditUserDialog({
  user,
  roles,
  isSelf,
  onOpenChange,
}: EditUserDialogProps) {
  const updateUser = useUpdateUser();

  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: user.full_name,
      roles: user.roles,
      is_active: user.is_active,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await updateUser.mutateAsync({
        userId: user.id,
        input: {
          full_name: values.full_name,
          // The API refuses these for your own account, so leave them out.
          ...(isSelf
            ? {}
            : { roles: values.roles, is_active: values.is_active }),
        },
      });

      toast.success("User updated");
      onOpenChange(false);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not update the user"));
    }
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit user</DialogTitle>

          <DialogDescription>{user.email}</DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          <div className="space-y-2">
            <Label htmlFor="edit-user-name">Full name</Label>

            <Input
              id="edit-user-name"
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
                  disabled={isSubmitting || isSelf}
                  emptyMessage="No roles exist yet."
                />
              )}
            />

            {isSelf ? (
              <p className="text-xs text-muted-foreground">
                You cannot change your own roles.
              </p>
            ) : null}
          </div>

          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <Label htmlFor="edit-user-active">Active</Label>

              <p className="text-xs text-muted-foreground">
                {isSelf
                  ? "You cannot deactivate your own account."
                  : "Inactive users cannot sign in."}
              </p>
            </div>

            <Controller
              control={control}
              name="is_active"
              render={({ field }) => (
                <Switch
                  id="edit-user-active"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  disabled={isSubmitting || isSelf}
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
              {isSubmitting ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
