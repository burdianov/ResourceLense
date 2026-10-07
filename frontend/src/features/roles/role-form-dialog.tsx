import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
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
import {
  useCreateRole,
  useUpdateRole,
} from "@/features/roles/use-roles";
import { apiErrorMessage } from "@/lib/api-error";
import type { PermissionRecord, Role } from "@/types/role";

const schema = z.object({
  name: z.string().min(2, "Use at least 2 characters").max(100, "Too long"),
  description: z.string().max(255, "Too long"),
  permissions: z.array(z.string()),
});

type FormValues = z.infer<typeof schema>;

type RoleFormDialogProps = {
  role?: Role;
  catalogue: PermissionRecord[];
  onOpenChange: (open: boolean) => void;
};

function groupPermissions(catalogue: PermissionRecord[]) {
  const groups = new Map<string, PermissionRecord[]>();

  for (const permission of catalogue) {
    const [resource] = permission.name.split(".");

    const key = resource || "other";

    groups.set(key, [...(groups.get(key) ?? []), permission]);
  }

  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

export function RoleFormDialog({
  role,
  catalogue,
  onOpenChange,
}: RoleFormDialogProps) {
  const createRole = useCreateRole();
  const updateRole = useUpdateRole();

  const isEdit = role !== undefined;

  const groups = useMemo(() => groupPermissions(catalogue), [catalogue]);

  const {
    control,
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: role?.name ?? "",
      description: role?.description ?? "",
      permissions: role?.permissions ?? [],
    },
  });

  const selected = useWatch({ control, name: "permissions" }) ?? [];

  function toggleGroup(names: string[], selectAll: boolean) {
    setValue(
      "permissions",
      selectAll
        ? [...new Set([...selected, ...names])]
        : selected.filter((name) => !names.includes(name)),
    );
  }

  const onSubmit = handleSubmit(async (values) => {
    const description = values.description.trim() || null;

    try {
      if (role) {
        await updateRole.mutateAsync({
          roleId: role.id,
          input: {
            name: values.name,
            description,
            permissions: values.permissions,
          },
        });

        toast.success(`Role "${values.name}" updated`);
      } else {
        await createRole.mutateAsync({
          name: values.name,
          description,
          permissions: values.permissions,
        });

        toast.success(`Role "${values.name}" created`);
      }

      onOpenChange(false);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not save the role"));
    }
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit role" : "New role"}</DialogTitle>

          <DialogDescription>
            Roles bundle permissions. Assign them to users on the Users
            screen.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          <div className="space-y-2">
            <Label htmlFor="role-name">Name</Label>

            <Input
              id="role-name"
              disabled={isSubmitting}
              aria-invalid={errors.name ? true : undefined}
              {...register("name")}
            />

            {errors.name ? (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            ) : (
              <p className="text-xs text-muted-foreground">
                Stored lower-case, for example &quot;project-manager&quot;.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-description">Description</Label>

            <Input
              id="role-description"
              disabled={isSubmitting}
              aria-invalid={errors.description ? true : undefined}
              {...register("description")}
            />

            {errors.description ? (
              <p className="text-sm text-destructive">
                {errors.description.message}
              </p>
            ) : null}
          </div>

          <div className="space-y-3">
            <Label>Permissions</Label>

            <Controller
              control={control}
              name="permissions"
              render={({ field }) => (
                <div className="space-y-4">
                  {groups.map(([resource, items]) => {
                    const names = items.map((item) => item.name);
                    const allSelected = names.every((name) =>
                      field.value.includes(name),
                    );

                    return (
                      <div key={resource} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-medium capitalize">
                            {resource}
                          </h3>

                          <Button
                            type="button"
                            variant="ghost"
                            size="xs"
                            disabled={isSubmitting}
                            onClick={() => toggleGroup(names, !allSelected)}
                          >
                            {allSelected ? "Clear all" : "Select all"}
                          </Button>
                        </div>

                        <CheckboxList
                          items={items.map((item) => ({
                            value: item.name,
                            label: item.name,
                            hint: item.description,
                          }))}
                          value={field.value}
                          onChange={field.onChange}
                          disabled={isSubmitting}
                          className="max-h-40"
                        />
                      </div>
                    );
                  })}
                </div>
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
              {isSubmitting
                ? "Saving..."
                : isEdit
                  ? "Save changes"
                  : "Create role"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
