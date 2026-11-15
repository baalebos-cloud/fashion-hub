import { useEffect, useState, type ReactNode } from "react";
import { Table, type Column } from "@/components/ui/table";
import { Pagination } from "@/components/ui/pagination";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { ListParams, Paged } from "@/api/admin-lists.api";

const PAGE_SIZE = 50;

export interface ListFilter { label: string; params: ListParams }

/** A read-only admin list: title with total, filter buttons, table and pages. */
export function AdminListPage<T extends { id: string }>({ title, intro, load, columns, filters, emptyTitle }: {
  title: string;
  intro?: ReactNode;
  load: (params: ListParams) => Promise<Paged<T>>;
  columns: Column<T>[];
  filters?: ListFilter[];
  emptyTitle: string;
}) {
  const [filter, setFilter] = useState(0);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paged<T> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);
    load({ ...(filters?.[filter]?.params ?? {}), page, page_size: PAGE_SIZE })
      .then((value) => { if (active) setData(value); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, `Couldn't load ${title.toLowerCase()}.`)); });
    return () => { active = false; };
    // `load` and `filters` are fixed per page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, page, attempt]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-xl text-ink">
          {title} {data && <span className="ml-2 text-sm font-normal text-ink-soft">({data.total})</span>}
        </h1>
        {filters && (
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter">
            {filters.map((f, i) => (
              <button key={f.label} type="button" aria-pressed={filter === i}
                onClick={() => { setFilter(i); setPage(1); setData(null); }}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                  filter === i ? "border-ink bg-ink text-paper" : "border-line text-ink-soft hover:border-ink hover:text-ink"}`}>
                {f.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {intro && <p className="text-sm text-ink-soft">{intro}</p>}
      {error && (
        <div className="flex flex-col items-start gap-2">
          <p role="alert" className="text-sm text-thread">{error}</p>
          <Button variant="secondary" size="sm" onClick={() => setAttempt((n) => n + 1)}>Try again</Button>
        </div>
      )}
      {!data && !error && <div className="flex justify-center py-16"><Spinner /></div>}
      {data && data.items.length === 0 && <EmptyState title={emptyTitle} />}
      {data && data.items.length > 0 && (
        <>
          <Table columns={columns} rows={data.items} />
          {data.total > PAGE_SIZE && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={setPage} />}
        </>
      )}
    </div>
  );
}
