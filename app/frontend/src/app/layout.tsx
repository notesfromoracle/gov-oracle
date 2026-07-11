import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";
import { Providers } from "./providers";

const GA_ID = process.env.NEXT_PUBLIC_GA_ID;

export const metadata: Metadata = {
  title: "Notes From Oracle — Government Transparency",
  description:
    "Measuring how transparent, navigable, and explainable public institutions are, using only publicly available data.",
};

const navLinks = [
  { href: "/governments", label: "Governments" },
  { href: "/methodology", label: "Methodology" },
  { href: "/sources", label: "Sources" },
  { href: "/about", label: "About" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
              <Link href="/" className="text-lg font-semibold tracking-tight">
                Notes From Oracle
              </Link>
              <nav className="flex gap-6 text-sm text-slate-600">
                {navLinks.map((link) => (
                  <Link key={link.href} href={link.href} className="hover:text-slate-900">
                    {link.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
          <footer className="border-t border-slate-200 bg-white">
            <div className="mx-auto max-w-6xl px-4 py-6 text-sm text-slate-500">
              Open-source public-information audit.
            </div>
          </footer>
        </Providers>
        {GA_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${GA_ID}');
              `}
            </Script>
          </>
        )}
      </body>
    </html>
  );
}
