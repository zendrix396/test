import "./globals.css";
import ClientLayout from "@/client-layout";
import AdminLayout from "@/components/AdminLayout/AdminLayout";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://space4u.in";
const siteName = "SPACE4U";
const siteDescription = "Discover Exclusive Merchandise for Every Fan - Anime, Superheroes, and Supervillains. Premium collectibles, action figures, and merchandise for devoted fans.";

export const metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: `${siteName} | Your Otaku Haven`,
    template: `%s | ${siteName}`,
  },
  description: siteDescription,
  keywords: [
    "anime merchandise",
    "anime collectibles",
    "action figures",
    "superhero merchandise",
    "otaku haven",
    "anime store",
    "collectibles",
    "manga merchandise",
    "anime figures",
  ],
  authors: [{ name: siteName }],
  creator: siteName,
  publisher: siteName,
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: siteUrl,
    siteName: siteName,
    title: `${siteName} | Your Otaku Haven`,
    description: siteDescription,
    images: [
      {
        url: "/home/hero.jpg",
        width: 1200,
        height: 630,
        alt: `${siteName} - Premium Anime Merchandise`,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${siteName} | Your Otaku Haven`,
    description: siteDescription,
    images: ["/home/hero.jpg"],
    creator: "@space4u",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  verification: {
    google: process.env.NEXT_PUBLIC_GOOGLE_VERIFICATION,
  },
  alternates: {
    canonical: siteUrl,
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/icon.png" />
        <link rel="apple-touch-icon" href="/icon.png" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700;900&family=Noto+Serif+JP:wght@200;400;700;900&display=swap" rel="stylesheet" />
      </head>
      <body>
        <ClientLayout>
          <AdminLayout>
          {children}
          </AdminLayout>
        </ClientLayout>
      </body>
    </html>
  );
}
