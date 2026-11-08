import { Link } from "react-router-dom";
import { useOrders } from "@/hooks/use-orders";
import { Greeting } from "@/components/common/Greeting";
import { SmartDesignSearch } from "@/components/search/SmartDesignSearch";
import { NearbyProfessionals } from "@/components/search/NearbyProfessionals";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { customerRoutes } from "@/config/routes.config";
import { CUSTOMER_ORDER_NEXT_STEP as NEXT_STEP } from "@/constants/order-status";
import type { CustomerOrderStatus, Order } from "@/types/order";

const FINISHED: CustomerOrderStatus[] = ["received", "completed", "cancelled", "rejected", "refunded"];


function ActiveOrder({ order }: { order: Order }) {
  const status = order.status as CustomerOrderStatus;
  const name = order.items[0]?.name_snapshot ?? order.order_number;
  return (
    <Link to={customerRoutes.orderDetails(order.id)}
      className="flex flex-col gap-1.5 rounded-control border border-line bg-surface p-3 transition-colors hover:border-indigo">
      <span className="flex flex-wrap items-center justify-between gap-2">
        <OrderStatusBadge status={status} />
        <span className="font-mono text-xs text-ink-soft">{order.order_number}</span>
      </span>
      <span className="font-semibold text-ink">{name}</span>
      {NEXT_STEP[status] && <span className="text-[13px] text-ink-soft">{NEXT_STEP[status]}</span>}
    </Link>
  );
}

export default function Dashboard() {
  const { orders, isLoading, error, refetch } = useOrders();
  const active = orders.filter((order) => !FINISHED.includes(order.status as CustomerOrderStatus));

  return (
    <div className="flex flex-col gap-10">
      <div className="grid gap-6 lg:grid-cols-12 lg:items-start">
        <section className="flex flex-col gap-5 lg:col-span-8" aria-label="Start an order">
          <Greeting subtitle="What would you like made?" />
          <SmartDesignSearch profilePathFor={customerRoutes.professionalDetails} />
        </section>

        <aside aria-label="Your orders" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4 lg:col-span-4">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="font-semibold text-ink">Your orders</h2>
            <Link to={customerRoutes.orders} className="text-sm font-semibold text-indigo">All orders</Link>
          </div>
          {isLoading && <SkeletonRows rows={2} label="Loading your orders" onRetry={refetch} />}
          {!isLoading && error && <ErrorState title="Couldn't load your orders" description="Check your connection, then try again." onRetry={refetch} />}
          {!isLoading && !error && active.length === 0 && (
            <p className="text-sm text-ink-soft">
              No orders in progress. {orders.length > 0 ? "Finished orders are under All orders." : "Find a tailor below to start one."}
            </p>
          )}
          {!isLoading && !error && active.slice(0, 3).map((order) => <ActiveOrder key={order.id} order={order} />)}
        </aside>
      </div>

      <section aria-label="Tailors near you" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="font-display text-2xl text-ink">Tailors near you</h2>
          <Link to={customerRoutes.findProfessionals}><Button variant="secondary" size="sm">Browse all</Button></Link>
        </div>
        <NearbyProfessionals detailsPathFor={customerRoutes.professionalDetails} />
      </section>

      <section aria-label="How an order works" className="flex flex-col gap-4">
        <h2 className="font-display text-xl text-ink">How an order works</h2>
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {[
            ["Choose a design", "From a tailor who's taking orders; the price is shown up front."],
            ["Add measurements", "Saved to your account for next time."],
            ["Pay and send", "The tailor accepts and starts making it."],
            ["Follow production", "Every step shows here and in messages."],
            ["Receive with a code", "Give your one-time code to the rider, then leave a review."],
          ].map(([title, body], index) => (
            <li key={title} className="flex flex-col gap-1">
              <span className="font-mono text-sm text-indigo">{index + 1}</span>
              <span className="font-semibold text-ink">{title}</span>
              <span className="text-sm text-ink-soft">{body}</span>
            </li>
          ))}
        </ol>
      </section>
      {orders.length === 0 && !isLoading && !error && (
        <EmptyState title="No orders yet" description="Search for a design above or browse tailors near you to place your first order." />
      )}
    </div>
  );
}
