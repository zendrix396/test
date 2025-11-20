"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import "./ScrollHero.css";

export default function ScrollHero() {
  const canvasRef = useRef(null);
  const contextRef = useRef(null);
  const imagesRef = useRef([]);
  const videoFramesRef = useRef({ frame: 0 });

  gsap.registerPlugin(ScrollTrigger);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    contextRef.current = context;

    const setCanvasSize = () => {
      const pixelRatio = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * pixelRatio;
      canvas.height = window.innerHeight * pixelRatio;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.scale(pixelRatio, pixelRatio);
    };

    setCanvasSize();

    const frameCount = 207;
    const currentFrame = (index) =>
      `/frames/frame_${(index + 1).toString().padStart(4, "0")}.jpg`;

    let images = [];
    let imagesToLoad = frameCount;

    const onLoad = () => {
      imagesToLoad--;
      if (!imagesToLoad) {
        render();
        setupScrollTrigger();
      }
    };

    for (let i = 0; i < frameCount; i++) {
      const img = new Image();
      img.onload = onLoad;
      img.onerror = function () {
        onLoad.call(this);
      };
      img.src = currentFrame(i);
      images.push(img);
    }

    imagesRef.current = images;

    const render = () => {
      const canvasWidth = window.innerWidth;
      const canvasHeight = window.innerHeight;

      context.clearRect(0, 0, canvasWidth, canvasHeight);

      const img = images[videoFramesRef.current.frame];
      if (img && img.complete && img.naturalWidth > 0) {
        const imageAspect = img.naturalWidth / img.naturalHeight;
        const canvasAspect = canvasWidth / canvasHeight;

        let drawWidth, drawHeight, drawX, drawY;

        if (imageAspect > canvasAspect) {
          drawHeight = canvasHeight;
          drawWidth = drawHeight * imageAspect;
          drawX = (canvasWidth - drawWidth) / 2;
          drawY = 0;
        } else {
          drawWidth = canvasWidth;
          drawHeight = drawWidth / imageAspect;
          drawX = 0;
          drawY = (canvasHeight - drawHeight) / 2;
        }

        context.drawImage(img, drawX, drawY, drawWidth, drawHeight);
      }
    };

    const setupScrollTrigger = () => {
      ScrollTrigger.create({
        start: 0,
        endTrigger: ".spotlight",
        end: "bottom top",
        scrub: 1,
        onUpdate: (self) => {
          const progress = self.progress;

          const animationProgress = Math.min(Math.max(progress, 0), 1);
          const targetFrame = Math.round(animationProgress * (frameCount - 1));
          videoFramesRef.current.frame = targetFrame;
          render();
        },
      });

      // Fallback if spotlight isn't present (ensure background still works)
      if (!document.querySelector(".spotlight")) {
        ScrollTrigger.create({
          start: 0,
          end: `+=${window.innerHeight * 6}px`,
          scrub: 1,
          onUpdate: (self) => {
            const progress = self.progress;
            const targetFrame = Math.round(progress * (frameCount - 1));
            videoFramesRef.current.frame = targetFrame;
            render();
          },
        });
      }
    };

    const handleResize = () => {
      setCanvasSize();
      render();
      ScrollTrigger.refresh();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      ScrollTrigger.getAll().forEach((st) => st.kill());
    };
  }, []);

  return (
    <>
      <canvas className="scroll-hero-canvas" ref={canvasRef}></canvas>
      <div className="scroll-hero-overlay"></div>
    </>
  );
}

