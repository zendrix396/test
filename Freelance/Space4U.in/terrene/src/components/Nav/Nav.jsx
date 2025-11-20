"use client";
import "./Nav.css";

import {
  useEffect,
  useState,
  useCallback,
  useRef,
  useLayoutEffect,
} from "react";
import { usePathname, useRouter } from "next/navigation";

import gsap from "gsap";
import CustomEase from "gsap/CustomEase";
import SplitText from "gsap/SplitText";
import { useLenis } from "lenis/react";

import MenuBtn from "../MenuBtn/MenuBtn";
import { useViewTransition } from "@/hooks/useViewTransition";
import { useUser } from "@/lib/hooks";
import fetchApi from "@/lib/api";

gsap.registerPlugin(SplitText);

const Nav = () => {
  const [isAnimating, setIsAnimating] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const menuRef = useRef(null);
  const isInitializedRef = useRef(false);
  const splitTextRefs = useRef([]);
  const router = useRouter();
  const pathname = usePathname();
  const lenis = useLenis();

  const { navigateWithTransition } = useViewTransition();
  const { user } = useUser();
  const [leaderboard, setLeaderboard] = useState([]);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const data = await fetchApi("/auth/leaderboard/");
        if (data && Array.isArray(data)) {
          setLeaderboard(data.slice(0, 10)); // Top 10 for nav
        }
      } catch (error) {
        console.error("Failed to fetch leaderboard:", error);
      }
    };
    fetchLeaderboard();
  }, []);

  useEffect(() => {
    if (lenis) {
      if (isOpen) {
        lenis.stop();
      } else {
        lenis.start();
      }
    }
  }, [lenis, isOpen]);

  useLayoutEffect(() => {
    gsap.registerPlugin(CustomEase);
    CustomEase.create(
      "hop",
      "M0,0 C0.354,0 0.464,0.133 0.498,0.502 0.532,0.872 0.651,1 1,1"
    );
  }, []);

  useLayoutEffect(() => {
    if (menuRef.current) {
      const menu = menuRef.current;

      splitTextRefs.current.forEach((split) => {
        if (split.revert) split.revert();
      });
      splitTextRefs.current = [];

      gsap.set(menu, {
        clipPath: "circle(0% at 50% 50%)",
      });

      const h2Elements = menu.querySelectorAll("h2");
      const pElements = menu.querySelectorAll("p");

      h2Elements.forEach((h2, index) => {
        const split = SplitText.create(h2, {
          type: "lines",
          mask: "lines",
          linesClass: "split-line",
        });

        gsap.set(split.lines, { y: "120%" });

        split.lines.forEach((line) => {
          line.style.pointerEvents = "auto";
        });

        splitTextRefs.current.push(split);
      });

      pElements.forEach((p, index) => {
        const split = SplitText.create(p, {
          type: "lines",
          mask: "lines",
          linesClass: "split-line",
        });

        gsap.set(split.lines, { y: "120%" });

        split.lines.forEach((line) => {
          line.style.pointerEvents = "auto";
        });

        splitTextRefs.current.push(split);
      });

      isInitializedRef.current = true;
    }
  }, []);

  const animateMenu = useCallback((open) => {
    if (!menuRef.current) {
      return;
    }

    const menu = menuRef.current;

    setIsAnimating(true);

    if (open) {
      document.body.classList.add("menu-open");

      gsap.to(menu, {
        clipPath: "circle(100% at 50% 50%)",
        ease: "power3.out",
        duration: 2,
        onStart: () => {
          menu.style.pointerEvents = "all";
        },
        onStart: () => {
          splitTextRefs.current.forEach((split, index) => {
            gsap.to(split.lines, {
              y: "0%",
              stagger: 0.05,
              delay: 0.35 + index * 0.1,
              duration: 1,
              ease: "power4.out",
            });
          });
        },
        onComplete: () => {
          setIsAnimating(false);
        },
      });
    } else {
      const textTimeline = gsap.timeline({
        onStart: () => {
          gsap.to(menu, {
            clipPath: "circle(0% at 50% 50%)",
            ease: "power3.out",
            duration: 1,
            delay: 0.75,
            onComplete: () => {
              menu.style.pointerEvents = "none";

              splitTextRefs.current.forEach((split) => {
                gsap.set(split.lines, { y: "120%" });
              });

              document.body.classList.remove("menu-open");

              setIsAnimating(false);
              setIsNavigating(false);
            },
          });
        },
      });

      splitTextRefs.current.forEach((split, index) => {
        textTimeline.to(
          split.lines,
          {
            y: "-120%",
            stagger: 0.03,
            delay: index * 0.05,
            duration: 1,
            ease: "power3.out",
          },
          0
        );
      });
    }
  }, []);

  useEffect(() => {
    if (isInitializedRef.current) {
      animateMenu(isOpen);
    }
  }, [isOpen, animateMenu]);

  const toggleMenu = useCallback(() => {
    if (!isAnimating && isInitializedRef.current && !isNavigating) {
      setIsOpen((prevIsOpen) => {
        return !prevIsOpen;
      });
    } else {
    }
  }, [isAnimating, isNavigating]);

  const handleLinkClick = useCallback(
    (e, href) => {
      e.preventDefault();

      const currentPath = window.location.pathname;
      if (currentPath === href) {
        if (isOpen) {
          setIsOpen(false);
        }
        return;
      }

      if (isNavigating) return;

      setIsNavigating(true);
      // Close menu immediately
      if (isOpen) {
        setIsOpen(false);
        // Force close the menu visually
        if (menuRef.current) {
          menuRef.current.style.pointerEvents = "none";
          document.body.classList.remove("menu-open");
        }
      }
      navigateWithTransition(href);
    },
    [isNavigating, navigateWithTransition, isOpen]
  );

  const splitTextIntoSpans = (text) => {
    return text
      .split("")
      .map((char, index) =>
        char === " " ? (
          <span key={index}>&nbsp;&nbsp;</span>
        ) : (
          <span key={index}>{char}</span>
        )
      );
  };

  return (
    <div>
      <MenuBtn isOpen={isOpen} toggleMenu={toggleMenu} />
      <div className="menu" ref={menuRef}>
        <div className="menu-wrapper">
          <div className="col col-1">
            <div className="links">
              <div className="link">
                <a href="/" onClick={(e) => handleLinkClick(e, "/")}>
                  <h2>Home</h2>
                </a>
              </div>
              {pathname !== "/shop" && (
                <div className="link">
                  <a
                    href="/shop"
                    onClick={(e) => handleLinkClick(e, "/shop")}
                  >
                    <h2>Shop</h2>
                  </a>
                </div>
              )}
              <div className="link">
                <a
                  href="/wishlist"
                  onClick={(e) => handleLinkClick(e, "/wishlist")}
                >
                  <h2>Wishlist</h2>
                </a>
              </div>
              <div className="link">
                <a
                  href="/cart"
                  onClick={(e) => handleLinkClick(e, "/cart")}
                >
                  <h2>Cart</h2>
                </a>
              </div>
              {user ? (
                <>
              <div className="link">
                <a
                  href="/profile"
                  onClick={(e) => handleLinkClick(e, "/profile")}
                >
                  <h2>Profile</h2>
                </a>
              </div>
                  <div className="link">
                    <a
                      href="/orders"
                      onClick={(e) => handleLinkClick(e, "/orders")}
                    >
                      <h2>Orders</h2>
                    </a>
                  </div>
                </>
              ) : (
                <div className="link">
                  <a
                    href="/login"
                    onClick={(e) => handleLinkClick(e, "/login")}
                  >
                    <h2>Login</h2>
                  </a>
                </div>
              )}
              <div className="link">
                <a
                  href="/connect"
                  onClick={(e) => handleLinkClick(e, "/connect")}
                >
                  <h2>Support</h2>
                </a>
              </div>
            </div>
          </div>
          <div className="col col-2">
            <div className="socials">
              <div className="sub-col">
                <div className="menu-meta menu-commissions">
                  <p>Contact Us</p>
                  <p>contactspace4u@gmail.com</p>
                  <p>+91 7355480402</p>
                </div>
                <div className="menu-meta">
                  <p>Mailing Address</p>
                  <p>Salempur Road, Gangaganj</p>
                  <p>Lucknow 226501</p>
                </div>
              </div>
              <div className="sub-col">
                <div className="menu-meta">
                  <p>Quick Links</p>
                  <p>Privacy Policies</p>
                  <p>S4U Policies</p>
                  <p>Orders</p>
                </div>
                <div className="menu-meta">
                  <a
                    href="/leaderboard"
                    onClick={(e) => handleLinkClick(e, "/leaderboard")}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <p>Leaderboard →</p>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Nav;
