import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/components/layout/app-layout";
import {
  PermissionRoute,
  ProtectedRoute,
} from "@/features/auth/protected-route";
import { RolesPage } from "@/pages/admin/roles-page";
import { UsersPage } from "@/pages/admin/users-page";
import { DashboardPage } from "@/pages/dashboard-page";
import { LoginPage } from "@/pages/login-page";
import { PlanningPage } from "@/pages/planning-page";
import { ProjectsPage } from "@/pages/projects-page";
import { ReportsPage } from "@/pages/reports-page";
import { ResourcesPage } from "@/pages/resources-page";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <DashboardPage />,
          },
          {
            path: "planning",
            element: <PlanningPage />,
          },
          {
            path: "projects",
            element: <ProjectsPage />,
          },
          {
            path: "resources",
            element: <ResourcesPage />,
          },
          {
            path: "reports",
            element: <ReportsPage />,
          },
          {
            element: <PermissionRoute permission="users.view" />,
            children: [
              {
                path: "admin/users",
                element: <UsersPage />,
              },
            ],
          },
          {
            element: <PermissionRoute permission="roles.view" />,
            children: [
              {
                path: "admin/roles",
                element: <RolesPage />,
              },
            ],
          },
        ],
      },
    ],
  },
]);
