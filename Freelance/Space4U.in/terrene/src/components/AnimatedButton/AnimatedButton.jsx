"use client";
import "./AnimatedButton.css";
import React, { useRef } from "react";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { useGSAP } from "@gsap/react";
import { useViewTransition } from "@/hooks/useViewTransition";

import { IoMdArrowForward } from "react-icons/io";

gsap.registerPlugin(SplitText, ScrollTrigger);

const AnimatedButton = ({
  label,
  route,
  animate = true,
  animateOnScroll = true,
  delay = 0,
  onClick,
  disabled = false,
  extraClasses = "",
}) => {
  const { navigateWithTransition } = useViewTransition();
  const buttonRef = useRef(null);
  const circleRef = useRef(null);
  const iconRef = useRef(null);
  const textRef = useRef(null);
  const splitRef = useRef(null);

  const waitForFonts = async () => {
    try {
      await document.fonts.ready;
      const customFonts = ["Manrope"];
      const fontCheckPromises = customFonts.map((fontFamily) => {
        return document.fonts.check(`16px ${fontFamily}`);
      });
      await Promise.all(fontCheckPromises);
      await new Promise((resolve) => setTimeout(resolve, 100));
      return true;
    } catch (error) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      return true;
    }
  };

  useGSAP(
    () => {
      if (!buttonRef.current || !textRef.current) return;

      if (!animate) {
        gsap.set(buttonRef.current, { scale: 1 });
        gsap.set(circleRef.current, { scale: 1, opacity: 1 });
        gsap.set(iconRef.current, { opacity: 1, x: 0 });
        return;
      }

      const initializeAnimation = async () => {
        await waitForFonts();

        const split = SplitText.create(textRef.current, {
          type: "lines",
          mask: "lines",
          linesClass: "line++",
          lineThreshold: 0.1,
        });
        splitRef.current = split;

        gsap.set(buttonRef.current, { scale: 0, transformOrigin: "center" });
        gsap.set(circleRef.current, {
          scale: 0,
          transformOrigin: "center",
          opacity: 0,
        });
        gsap.set(iconRef.current, { opacity: 0, x: -20 });
        gsap.set(split.lines, { y: "100%", opacity: 0 });

        const tl = gsap.timeline({ delay: delay });

        tl.to(buttonRef.current, {
          scale: 1,
          duration: 0.5,
          ease: "back.out(1.7)",
        });

        tl.to(
          circleRef.current,
          {
            scale: 1,
            opacity: 1,
            duration: 0.5,
            ease: "power3.out",
          },
          "+0.25"
        );

        tl.to(
          iconRef.current,
          {
            opacity: 1,
            x: 0,
            duration: 0.5,
            ease: "power3.out",
          },
          "-0.25"
        );

        tl.to(
          split.lines,
          {
            y: "0%",
            opacity: 1,
            duration: 0.8,
            stagger: 0.1,
            ease: "power4.out",
          },
          "-=0.2"
        );

        if (animateOnScroll) {
          ScrollTrigger.create({
            trigger: buttonRef.current,
            start: "top 90%",
            once: true,
            animation: tl,
          });
        }
      };

      initializeAnimation();

      return () => {
        if (splitRef.current) {
          splitRef.current.revert();
        }
      };
    },
    { scope: buttonRef, dependencies: [animate, animateOnScroll, delay] }
  );

  const buttonContent = (
    <>
      <span className="circle" ref={circleRef} aria-hidden="true"></span>
      <div className="icon" ref={iconRef}>
        <IoMdArrowForward />
      </div>
      <span className="button-text" ref={textRef}>
        {label}
      </span>
    </>
  );

  const className = `btn ${extraClasses}`.trim();

  if (route && !onClick) {
    return (
      <a
        href={route}
        className={className}
        ref={buttonRef}
        onClick={(e) => {
          e.preventDefault();
          navigateWithTransition(route);
        }}
      >
        {buttonContent}
      </a>
    );
  }

  return (
    <button className={className} ref={buttonRef} onClick={onClick} disabled={disabled}>
      {buttonContent}
    </button>
  );
};

export default AnimatedButton;
