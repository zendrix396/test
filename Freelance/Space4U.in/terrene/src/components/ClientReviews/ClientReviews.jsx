"use client";
import "./ClientReviews.css";
import clientReviewsContent from "./client-reviews-content";

import { useState, useEffect, useRef, useCallback } from "react";

import { gsap } from "gsap";
import { SplitText } from "gsap/SplitText";

const ClientReviews = () => {
  const [activeClient, setActiveClient] = useState(0);
  const [visualClient, setVisualClient] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const clientRefs = useRef([]);
  const containerRef = useRef(null);
  const reviewTextRef = useRef(null);
  const splitTextRef = useRef(null);
  const clientInfoRefs = useRef([]);
  const imageContainerRef = useRef(null);
  const masterTimelineRef = useRef(null);

  const getBaseItemWidth = useCallback(() => {
    if (typeof window === "undefined") {
      return "2.75rem";
    }

    return window.innerWidth <= 768 ? "2.5rem" : "2.75rem";
  }, []);

  const getExpandedWidth = useCallback(() => {
    if (!containerRef.current) return "12rem";

    const baseItemWidth = getBaseItemWidth();
    const isSmallScreen = baseItemWidth === "2.5rem";
    const containerWidth = containerRef.current.offsetWidth;
    const padding = isSmallScreen ? 12 : 16; // total horizontal padding
    const gap = isSmallScreen ? 8 : 12;
    const inactiveItemWidth = isSmallScreen ? 40 : 44;
    const inactiveItems = clientReviewsContent.length - 1;

    const remainingSpace =
      containerWidth -
      padding -
      inactiveItemWidth * inactiveItems -
      gap * inactiveItems;

    if (remainingSpace <= 0) {
      return `${Math.max(inactiveItemWidth + 12, 96)}px`;
    }

    const minWidth = isSmallScreen ? 96 : 220;
    const maxWidth = isSmallScreen ? 180 : 400;

    let desiredWidth = Math.min(remainingSpace, maxWidth);

    if (remainingSpace >= minWidth) {
      desiredWidth = Math.max(desiredWidth, minWidth);
    } else {
      desiredWidth = remainingSpace;
    }

    if (desiredWidth > remainingSpace) {
      desiredWidth = remainingSpace;
    }

    return `${desiredWidth}px`;
  }, [getBaseItemWidth]);

  const animateImageChange = (newImageSrc) => {
    if (!imageContainerRef.current) return;

    const newImg = document.createElement("img");
    newImg.src = newImageSrc;
    newImg.alt = "";
    newImg.style.opacity = "0";

    imageContainerRef.current.appendChild(newImg);

    return gsap.to(newImg, {
      opacity: 1,
      duration: 1,
      delay: 0.5,
      ease: "power2.out",
      onComplete: () => {
        const allImages = imageContainerRef.current.querySelectorAll("img");
        allImages.forEach((img) => {
          if (img !== newImg) {
            img.remove();
          }
        });
      },
    });
  };

  useEffect(() => {
    const baseItemWidth = getBaseItemWidth();

    gsap.set(clientRefs.current, {
      width: baseItemWidth,
    });

    gsap.set(clientInfoRefs.current, {
      opacity: 0,
    });

    if (clientRefs.current[0]) {
      const expandedWidth = getExpandedWidth();
      gsap.to(clientRefs.current[0], {
        width: expandedWidth,
        duration: 0.7,
        ease: "power4.inOut",
      });
    }

    if (clientInfoRefs.current[0]) {
      gsap.to(clientInfoRefs.current[0], {
        opacity: 1,
        duration: 0.3,
        ease: "power2.out",
      });
    }

    const initTimer = setTimeout(() => {
      if (reviewTextRef.current) {
        splitTextRef.current = SplitText.create(reviewTextRef.current, {
          type: "lines",
          mask: "lines",
        });

        if (splitTextRef.current && splitTextRef.current.lines) {
          gsap.set(splitTextRef.current.lines, { y: "110%" });
          gsap.to(splitTextRef.current.lines, {
            y: "0%",
            duration: 0.5,
            stagger: 0.05,
            ease: "power4.out",
          });
        }
      }
    }, 100);

    return () => {
      clearTimeout(initTimer);
      if (splitTextRef.current) {
        splitTextRef.current.revert();
        splitTextRef.current = null;
      }
    };
  }, [getBaseItemWidth, getExpandedWidth]);

  useEffect(() => {
    if (!splitTextRef.current) return;

    if (reviewTextRef.current) {
      if (splitTextRef.current) {
        splitTextRef.current.revert();
      }

      splitTextRef.current = SplitText.create(reviewTextRef.current, {
        type: "lines",
        mask: "lines",
      });

      if (splitTextRef.current.lines) {
        gsap.set(splitTextRef.current.lines, { y: "110%" });

        gsap.to(splitTextRef.current.lines, {
          y: "0%",
          duration: 0.5,
          stagger: 0.05,
          ease: "power4.out",
        });
      }
    }
  }, [activeClient]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (reviewTextRef.current) {
        if (!splitTextRef.current) {
          splitTextRef.current = SplitText.create(reviewTextRef.current, {
            type: "lines",
            mask: "lines",
          });
        }

        if (splitTextRef.current && splitTextRef.current.lines) {
          gsap.set(splitTextRef.current.lines, { y: "110%" });
          gsap.to(splitTextRef.current.lines, {
            y: "0%",
            duration: 0.5,
            stagger: 0.05,
            ease: "power4.out",
          });
        }
      }
    }, 150);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleResize = () => {
      const baseItemWidth = getBaseItemWidth();

      clientRefs.current.forEach((ref, idx) => {
        if (!ref) return;
        if (idx !== activeClient) {
          gsap.set(ref, { width: baseItemWidth });
        }
      });

      if (clientRefs.current[activeClient]) {
        const expandedWidth = getExpandedWidth();
        gsap.set(clientRefs.current[activeClient], { width: expandedWidth });
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [activeClient, getBaseItemWidth, getExpandedWidth]);

  const handleClientClick = (index) => {
    if (index === activeClient || isAnimating) return;

    if (masterTimelineRef.current) {
      masterTimelineRef.current.kill();
    }

    setIsAnimating(true);

    const baseItemWidth = getBaseItemWidth();
    const expandedWidth = getExpandedWidth();

    masterTimelineRef.current = gsap.timeline();
    const tl = masterTimelineRef.current;

    if (clientInfoRefs.current[visualClient]) {
      tl.to(
        clientInfoRefs.current[visualClient],
        {
          opacity: 0,
          duration: 0.5,
          ease: "power2.out",
        },
        0
      );
    }

    tl.to(
      clientRefs.current[activeClient],
      {
        width: baseItemWidth,
        duration: 0.7,
        ease: "power4.inOut",
      },
      0
    ).to(
      clientRefs.current[index],
      {
        width: expandedWidth,
        duration: 0.7,
        ease: "power4.inOut",
      },
      0
    );

    tl.call(
      () => {
        setVisualClient(index);
      },
      [],
      0.2
    );

    tl.to(
      {},
      {
        duration: 0.1,
        onComplete: () => {
          if (clientInfoRefs.current[index]) {
            const clientInfoAnim = gsap.to(clientInfoRefs.current[index], {
              opacity: 0,
              duration: 0,
              ease: "power2.out",
              onComplete: () => {
                gsap.to(clientInfoRefs.current[index], {
                  opacity: 1,
                  duration: 0.5,
                  ease: "power2.out",
                });
              },
            });
            tl.add(clientInfoAnim, 0.5);
          }
        },
      },
      0.5
    );

    const imageAnimation = animateImageChange(
      clientReviewsContent[index].image
    );
    tl.add(imageAnimation, 0);

    if (splitTextRef.current && splitTextRef.current.lines) {
      const textOutAnim = gsap.to(splitTextRef.current.lines, {
        y: "-110%",
        duration: 0.5,
        stagger: 0.05,
        ease: "power4.in",
        onComplete: () => {
          setActiveClient(index);
        },
      });
      tl.add(textOutAnim, 0);
    } else {
      setActiveClient(index);
    }

    tl.call(() => {
      setTimeout(() => {
        setIsAnimating(false);
        masterTimelineRef.current = null;
      }, 250);
    });
  };

  return (
    <div className="client-reviews">
      <div className="container">
        <div className="client-reviews-wrapper">
          <div className="client-reviews-header-callout">
            <p>What our fans say</p>
          </div>
          <div className="client-review-content">
            <div className="client-review-img" ref={imageContainerRef}>
              <img src={clientReviewsContent[activeClient].image} alt="" />
            </div>
            <div className="client-review-copy">
              <h3 ref={reviewTextRef} key={activeClient}>
                {clientReviewsContent[activeClient].review}
              </h3>
            </div>
          </div>
          <div className="clients-list" ref={containerRef}>
            {clientReviewsContent.map((client, index) => (
              <div
                key={client.id}
                ref={(el) => (clientRefs.current[index] = el)}
                className={`client-item ${
                  index === visualClient ? "active" : ""
                } ${isAnimating ? "animating" : ""}`}
                onClick={() => handleClientClick(index)}
              >
                <div className="client-avatar">
                  <img src={client.avatar} alt={client.name} />
                </div>
                {index === visualClient && (
                  <div
                    className="client-info"
                    ref={(el) => (clientInfoRefs.current[index] = el)}
                    style={{ opacity: 0 }}
                  >
                    <p className="client-name md">{client.name}</p>
                    <p className="client-title">{client.title}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientReviews;
