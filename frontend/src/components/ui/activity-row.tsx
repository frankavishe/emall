import type { ReactNode } from "react";
import { Avatar } from "./avatar";

type ActivityRowProps = {
  name: string;
  description: string;
  badge?: ReactNode;
};

export function ActivityRow({ name, description, badge }: ActivityRowProps) {
  return (
    <li className="flex items-center justify-between gap-3 py-2">
      <div className="flex items-center gap-3 min-w-0">
        <Avatar name={name} size="sm" />
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-medium text-text-primary">{name}</span>
          <span className="truncate text-xs text-text-muted">{description}</span>
        </div>
      </div>
      {badge}
    </li>
  );
}
