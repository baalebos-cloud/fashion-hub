import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { publicRoutes, authRoutes } from "@/config/routes.config";

export default function Home() {
  return (
    <div>
      <section className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-4 py-24 text-center">
        <h1 className="font-display text-4xl text-ink sm:text-5xl">Custom clothing, made by people who know their craft.</h1>
        <p className="max-w-xl text-ink-soft">
          Find verified tailors and designers near you, order custom pieces with your own measurements, and track
          everything from fitting to doorstep.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link to={publicRoutes.findTailor}><Button size="lg">Find a tailor</Button></Link>
          <Link to={authRoutes.signup}><Button size="lg" variant="secondary">Join as a professional</Button></Link>
        </div>
      </section>

      <section className="border-t border-line bg-muslin/40 px-4 py-16">
        <div className="mx-auto grid max-w-4xl gap-8 sm:grid-cols-3">
          {[
            { title: "Find your tailor", body: "Browse verified professionals near you, filtered by specialty and style." },
            { title: "Order with confidence", body: "Submit your measurements, pick a delivery location, and pay securely." },
            { title: "Track every step", body: "From production to your doorstep, watch your order move in real time." },
          ].map((item) => (
            <div key={item.title}>
              <h3 className="font-display text-lg text-ink">{item.title}</h3>
              <p className="mt-1.5 text-sm text-ink-soft">{item.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
