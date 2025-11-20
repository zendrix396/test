"use client";
import "./TopBar.css";

import { useRef, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";

import gsap from "gsap";
import ScrollTrigger from "gsap/ScrollTrigger";

import { useViewTransition } from "@/hooks/useViewTransition";
import AnimatedButton from "../AnimatedButton/AnimatedButton";
import { useCartContext } from "@/context/CartContext";

gsap.registerPlugin(ScrollTrigger);

const TopBar = () => {
  const topBarRef = useRef(null);
  const { navigateWithTransition } = useViewTransition();
  const pathname = usePathname();
  const { openCart } = useCartContext();
  let lastScrollY = 0;
  let isScrolling = false;

  useEffect(() => {
    const topBar = topBarRef.current;
    if (!topBar) return;

    const topBarHeight = topBar.offsetHeight;

    gsap.set(topBar, { y: 0 });

    const handleScroll = () => {
      if (isScrolling) return;

      isScrolling = true;
      const currentScrollY = window.scrollY;
      const direction = currentScrollY > lastScrollY ? 1 : -1;

      if (direction === 1 && currentScrollY > 50) {
        gsap.to(topBar, {
          y: -topBarHeight,
          duration: 1,
          ease: "power4.out",
        });
      } else if (direction === -1) {
        gsap.to(topBar, {
          y: 0,
          duration: 1,
          ease: "power4.out",
        });
      }

      lastScrollY = currentScrollY;

      setTimeout(() => {
        isScrolling = false;
      }, 100);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  useEffect(() => {
    if (topBarRef.current) {
      gsap.set(topBarRef.current, { y: 0 });
    }
  });

  const handleCtaClick = useCallback(() => {
    if (pathname === "/shop") {
      openCart();
    } else {
      navigateWithTransition("/shop");
    }
  }, [pathname, openCart, navigateWithTransition]);

  return (
    <div className="top-bar" ref={topBarRef}>
      <div className="top-bar-logo">
        <a
          href="/"
          onClick={(e) => {
            e.preventDefault();
            navigateWithTransition("/");
          }}
        >
          <img src="/logos/terrene-logo.png" alt="" />
        </a>
      </div>
      <div className="top-bar-cta">
        <AnimatedButton
          label={pathname === "/shop" ? "Cart" : "Shop"}
          route={pathname === "/shop" ? undefined : "/shop"}
          animate={false}
          onClick={handleCtaClick}
        />
      </div>
    </div>
  );
};

export default TopBar;
