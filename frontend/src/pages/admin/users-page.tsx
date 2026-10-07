import { MoreHorizontal, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
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
import { useCurrentUser } from "@/features/auth/use-current-user";
import { useHasPermission } from "@/features/auth/use-permissions";
import { useRoles } from "@/features/roles/use-roles";
import { CreateUserDialog } from "@/features/users/create-user-dialog";
import { EditUserDialog } from "@/features/users/edit-user-dialog";
import { ResetPasswordDialog } from "@/features/users/reset-password-dialog";
import { useUpdateUser, useUsers } from "@/features/users/use-users";
import { apiErrorMessage } from "@/lib/api-error";
import type { UserSummary } from "@/types/user";

export function UsersPage() {
  const { data: users, isPending, isError, error } = useUsers();
  const { data: roles } = useRoles();
  const { data: currentUser } = useCurrentUser();
  const updateUser = useUpdateUser();

  const canEdit = useHasPermission("users.edit");

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<UserSummary | null>(null);
  const [resetting, setResetting] = useState<UserSummary | null>(null);

  const roleList = roles ?? [];

  async function toggleActive(user: UserSummary) {
    try {
      await updateUser.mutateAsync({
        userId: user.id,
        input: { is_active: !user.is_active },
      });

      toast.success(
        user.is_active
          ? `${user.email} deactivated`
          : `${user.email} activated`,
      );
    } catch (requestError) {
      toast.error(
        apiErrorMessage(requestError, "Could not update the user"),
      );
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Users"
        description="Manage ResourceLense sign-in accounts and access."
        actions={
          <Can permission="users.create">
            <Button onClick={() => setCreating(true)}>
              <Plus data-icon="inline-start" />
              New user
            </Button>
          </Can>
        }
      />

      {isError ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {apiErrorMessage(error, "Could not load users.")}
        </p>
      ) : null}

      {isPending ? (
        <div className="space-y-2">
          {[0, 1, 2].map((row) => (
            <Skeleton key={row} className="h-12 w-full" />
          ))}
        </div>
      ) : null}

      {users ? (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Roles</TableHead>
                <TableHead>Status</TableHead>
                {canEdit ? <TableHead className="w-10" /> : null}
              </TableRow>
            </TableHeader>

            <TableBody>
              {users.map((user) => {
                const isSelf = user.id === currentUser?.id;

                return (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="font-medium">{user.full_name}</div>

                      <div className="text-muted-foreground">
                        {user.email}
                        {isSelf ? " (you)" : ""}
                      </div>
                    </TableCell>

                    <TableCell>
                      {user.roles.length === 0 ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {user.roles.map((role) => (
                            <Badge key={role} variant="secondary">
                              {role}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </TableCell>

                    <TableCell>
                      <Badge
                        variant={user.is_active ? "outline" : "destructive"}
                      >
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>

                    {canEdit ? (
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            render={
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label={`Actions for ${user.email}`}
                              />
                            }
                          >
                            <MoreHorizontal />
                          </DropdownMenuTrigger>

                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => setEditing(user)}
                            >
                              Edit user
                            </DropdownMenuItem>

                            <DropdownMenuItem
                              onClick={() => setResetting(user)}
                            >
                              Reset password
                            </DropdownMenuItem>

                            <DropdownMenuItem
                              disabled={isSelf}
                              onClick={() => toggleActive(user)}
                            >
                              {user.is_active ? "Deactivate" : "Activate"}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    ) : null}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {users && users.length === 0 ? (
        <p className="text-sm text-muted-foreground">No users yet.</p>
      ) : null}

      {creating ? (
        <CreateUserDialog
          roles={roleList}
          onOpenChange={(open) => setCreating(open)}
        />
      ) : null}

      {editing ? (
        <EditUserDialog
          user={editing}
          roles={roleList}
          isSelf={editing.id === currentUser?.id}
          onOpenChange={(open) => {
            if (!open) {
              setEditing(null);
            }
          }}
        />
      ) : null}

      {resetting ? (
        <ResetPasswordDialog
          user={resetting}
          onOpenChange={(open) => {
            if (!open) {
              setResetting(null);
            }
          }}
        />
      ) : null}
    </div>
  );
}
