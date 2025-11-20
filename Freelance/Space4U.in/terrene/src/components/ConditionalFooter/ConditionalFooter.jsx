"use client";
import { usePathname } from "next/navigation";

import Footer from "@/components/Footer/Footer";

const ConditionalFooter = () => {
  const pathname = usePathname();
  // Show footer on all pages
  const showFooter = true;

  return showFooter ? <Footer /> : null;
};

export default ConditionalFooter;
