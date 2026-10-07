import { MoreHorizontal, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Can } from "@/features/auth/can";
import { useHasPermission } from "@/features/auth/use-permissions";
import { RoleFormDialog } from "@/features/roles/role-form-dialog";
import {
  useDeleteRole,
  usePermissionCatalogue,
  useRoles,
} from "@/features/roles/use-roles";
import { apiErrorMessage } from "@/lib/api-error";
import type { Role } from "@/types/role";

export function RolesPage() {
  const { data: roles, isPending, isError, error } = useRoles();
  const { data: catalogue } = usePermissionCatalogue();
  const deleteRole = useDeleteRole();

  const canEdit = useHasPermission("roles.edit");
  const canDelete = useHasPermission("roles.delete");

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Role | null>(null);
  const [deleting, setDeleting] = useState<Role | null>(null);

  const permissions = catalogue ?? [];

  async function confirmDelete() {
    if (!deleting) {
      return;
    }

    try {
      await deleteRole.mutateAsync(deleting.id);
      toast.success(`Role "${deleting.name}" deleted`);
      setDeleting(null);
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, "Could not delete the role"));
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Roles"
        description="Group permissions into roles and assign them to users."
        actions={
          <Can permission="roles.create">
            <Button onClick={() => setCreating(true)}>
              <Plus data-icon="inline-start" />
              New role
            </Button>
          </Can>
        }
      />

      {isError ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {apiErrorMessage(error, "Could not load roles.")}
        </p>
      ) : null}

      {isPending ? (
        <div className="space-y-2">
          {[0, 1, 2].map((row) => (
            <Skeleton key={row} className="h-12 w-full" />
          ))}
        </div>
      ) : null}

      {roles ? (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Role</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead>Users</TableHead>
                {canEdit || canDelete ? <TableHead className="w-10" /> : null}
              </TableRow>
            </TableHeader>

            <TableBody>
              {roles.map((role) => (
                <TableRow key={role.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{role.name}</span>

                      {role.is_protected ? (
                        <Badge variant="outline">Built-in</Badge>
                      ) : null}
                    </div>

                    {role.description ? (
                      <div className="text-muted-foreground">
                        {role.description}
                      </div>
                    ) : null}
                  </TableCell>

                  <TableCell>
                    <Badge variant="secondary">
                      {role.permissions.length}
                    </Badge>
                  </TableCell>

                  <TableCell>{role.user_count}</TableCell>

                  {canEdit || canDelete ? (
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          render={
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label={`Actions for ${role.name}`}
                            />
                          }
                        >
                          <MoreHorizontal />
                        </DropdownMenuTrigger>

                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            disabled={!canEdit || role.is_protected}
                            onClick={() => setEditing(role)}
                          >
                            Edit role
                          </DropdownMenuItem>

                          <DropdownMenuItem
                            variant="destructive"
                            disabled={!canDelete || role.is_protected}
                            onClick={() => setDeleting(role)}
                          >
                            Delete role
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {creating ? (
        <RoleFormDialog
          catalogue={permissions}
          onOpenChange={(open) => setCreating(open)}
        />
      ) : null}

      {editing ? (
        <RoleFormDialog
          role={editing}
          catalogue={permissions}
          onOpenChange={(open) => {
            if (!open) {
              setEditing(null);
            }
          }}
        />
      ) : null}

      <AlertDialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleting(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete role</AlertDialogTitle>

            <AlertDialogDescription>
              Delete the role &quot;{deleting?.name}&quot;? This cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>

            <AlertDialogAction
              variant="destructive"
              disabled={deleteRole.isPending}
              onClick={confirmDelete}
            >
              {deleteRole.isPending ? "Deleting..." : "Delete role"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
