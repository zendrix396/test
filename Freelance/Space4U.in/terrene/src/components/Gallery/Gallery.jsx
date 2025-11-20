"use client";
import "./Gallery.css";
import items from "./items";

import { useEffect, useRef, useState } from "react";

import gsap from "gsap";
import { CustomEase } from "gsap/dist/CustomEase";

let SplitType;

export default function Gallery() {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayRef = useRef(null);
  const projectTitleRef = useRef(null);
  const expandedItemRef = useRef(null);

  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const importSplitType = async () => {
      const SplitTypeModule = await import("split-type");
      SplitType = SplitTypeModule.default;

      setTimeout(() => {
        initializeGallery();
        setInitialized(true);
      }, 10);
    };

    gsap.registerPlugin(CustomEase);
    CustomEase.create("hop", "0.9, 0, 0.1, 1");

    importSplitType();

    return () => {
      if (containerRef.current) {
        containerRef.current.removeEventListener("mousedown", handleMouseDown);
        containerRef.current.removeEventListener(
          "touchstart",
          handleTouchStart
        );
      }

      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
      window.removeEventListener("resize", handleResize);

      if (stateRef.current.animationFrameId) {
        cancelAnimationFrame(stateRef.current.animationFrameId);
        stateRef.current.animationFrameId = null;
      }

      if (
        stateRef.current.expandedItem &&
        stateRef.current.expandedItem.parentNode
      ) {
        document.body.removeChild(stateRef.current.expandedItem);
        stateRef.current.expandedItem = null;
      }

      if (overlayRef.current) {
        overlayRef.current.classList.remove("active");
      }

      stateRef.current.isExpanded = false;
      stateRef.current.activeItem = null;
      stateRef.current.originalPosition = null;
      stateRef.current.activeItemId = null;
      stateRef.current.canDrag = true;

      if (stateRef.current.titleSplit) {
        stateRef.current.titleSplit.revert();
        stateRef.current.titleSplit = null;
      }
    };
  }, []);

  useEffect(() => {
    if (
      initialized &&
      canvasRef.current &&
      !stateRef.current.animationFrameId
    ) {
      animate();
    }
  }, [initialized]);

  useEffect(() => {
    const cleanupExpandedItem = () => {
      if (
        stateRef.current.expandedItem &&
        stateRef.current.expandedItem.parentNode
      ) {
        document.body.removeChild(stateRef.current.expandedItem);
        stateRef.current.expandedItem = null;
      }

      if (overlayRef.current) {
        overlayRef.current.classList.remove("active");
      }

      stateRef.current.isExpanded = false;
      stateRef.current.activeItem = null;
      stateRef.current.originalPosition = null;
      stateRef.current.activeItemId = null;
      stateRef.current.canDrag = true;

      if (stateRef.current.titleSplit) {
        stateRef.current.titleSplit.revert();
        stateRef.current.titleSplit = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        cleanupExpandedItem();
      }
    };

    const handleBeforeUnload = () => {
      cleanupExpandedItem();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      cleanupExpandedItem();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, []);

  const itemCount = 20;
  const itemGap = 150;
  const columns = 4;
  const itemWidth = 120;
  const itemHeight = 160;
  const masonryOffset = 125;

  const stateRef = useRef({
    isDragging: false,
    startX: 0,
    startY: 0,
    targetX: 0,
    targetY: 0,
    currentX: 0,
    currentY: 0,
    dragVelocityX: 0,
    dragVelocityY: 0,
    lastDragTime: 0,
    mouseHasMoved: false,
    visibleItems: new Set(),
    lastUpdateTime: 0,
    lastX: 0,
    lastY: 0,
    isExpanded: false,
    activeItem: null,
    canDrag: true,
    originalPosition: null,
    expandedItem: null,
    activeItemId: null,
    titleSplit: null,
    animationFrameId: null,
    introAnimationPlayed: false,
  });

  const setAndAnimateTitle = (title) => {
    const { titleSplit } = stateRef.current;
    const projectTitleElement = projectTitleRef.current.querySelector("p");

    if (titleSplit) titleSplit.revert();
    projectTitleElement.textContent = title;

    stateRef.current.titleSplit = new SplitType(projectTitleElement, {
      types: "words",
    });
    gsap.set(stateRef.current.titleSplit.words, { y: "100%" });
  };

  const animateTitleIn = () => {
    gsap.to(stateRef.current.titleSplit.words, {
      y: "0%",
      duration: 1,
      stagger: 0.1,
      ease: "power3.out",
    });
  };

  const animateTitleOut = () => {
    gsap.to(stateRef.current.titleSplit.words, {
      y: "-100%",
      duration: 1,
      stagger: 0.1,
      ease: "power3.out",
    });
  };

  const playIntroAnimation = () => {
    if (stateRef.current.introAnimationPlayed) return;

    const allItems = document.querySelectorAll(".item");
    if (allItems.length === 0) return;

    stateRef.current.introAnimationPlayed = true;

    gsap.to(allItems, {
      scale: 1,
      delay: 1,
      duration: 0.5,
      stagger: {
        amount: 1,
        from: "random",
      },
      ease: "power1.out",
    });
  };

  const updateVisibleItems = () => {
    const state = stateRef.current;
    const canvas = canvasRef.current;

    if (!canvas) return;

    const isMobile = window.innerWidth <= 1000;
    const buffer = isMobile ? 0.8 : 1.5;
    const viewWidth = window.innerWidth * (1 + buffer);
    const viewHeight = window.innerHeight * (1 + buffer);
    const movingRight = state.targetX > state.currentX;
    const movingDown = state.targetY > state.currentY;
    const directionBufferX = movingRight
      ? isMobile
        ? -100
        : -200
      : isMobile
      ? 100
      : 200;
    const directionBufferY = movingDown
      ? isMobile
        ? -100
        : -200
      : isMobile
      ? 100
      : 200;

    const startCol = Math.floor(
      (-state.currentX - viewWidth / 2 + (movingRight ? directionBufferX : 0)) /
        (itemWidth + itemGap)
    );
    const endCol = Math.ceil(
      (-state.currentX +
        viewWidth * (isMobile ? 1.0 : 1.2) +
        (!movingRight ? directionBufferX : 0)) /
        (itemWidth + itemGap)
    );
    const startRow = Math.floor(
      (-state.currentY - viewHeight / 2 + (movingDown ? directionBufferY : 0)) /
        (itemHeight + itemGap)
    );
    const endRow = Math.ceil(
      (-state.currentY +
        viewHeight * (isMobile ? 1.0 : 1.2) +
        (!movingDown ? directionBufferY : 0)) /
        (itemHeight + itemGap)
    );

    const currentItems = new Set();
    let newItemsCreated = false;

    for (let row = startRow; row <= endRow; row++) {
      for (let col = startCol; col <= endCol; col++) {
        const itemId = `${col},${row}`;
        currentItems.add(itemId);

        if (state.visibleItems.has(itemId)) continue;
        if (state.activeItemId === itemId && state.isExpanded) continue;

        const item = document.createElement("div");
        item.className = "item";
        item.id = itemId;

        const isEvenRow = row % 2 === 0;
        const horizontalOffset = isEvenRow ? masonryOffset : 0;
        item.style.left = `${col * (itemWidth + itemGap) + horizontalOffset}px`;
        item.style.top = `${row * (itemHeight + itemGap)}px`;
        item.dataset.col = col;
        item.dataset.row = row;

        if (!state.introAnimationPlayed) {
          gsap.set(item, { scale: 0 });
        }

        const itemNum = (Math.abs(row * columns + col) % itemCount) + 1;
        const img = document.createElement("img");
        img.src = `/archive/archive-${itemNum}.jpg`;
        img.alt = `Image ${itemNum}`;
        item.appendChild(img);

        item.addEventListener("click", (e) => {
          if (state.mouseHasMoved || state.isDragging) return;
          handleItemClick(item);
        });

        canvas.appendChild(item);
        state.visibleItems.add(itemId);
        newItemsCreated = true;
      }
    }

    state.visibleItems.forEach((itemId) => {
      if (
        !currentItems.has(itemId) ||
        (state.activeItemId === itemId && state.isExpanded)
      ) {
        const item = document.getElementById(itemId);
        if (item && canvas.contains(item)) canvas.removeChild(item);
        state.visibleItems.delete(itemId);
      }
    });

    if (newItemsCreated && !state.introAnimationPlayed) {
      playIntroAnimation();
    }
  };

  const handleItemClick = (item) => {
    const state = stateRef.current;

    if (state.isExpanded) {
      if (state.expandedItem) closeExpandedItem();
    } else {
      expandItem(item);
    }
  };

  const expandItem = (item) => {
    const state = stateRef.current;
    const container = containerRef.current;
    const overlay = overlayRef.current;

    state.isExpanded = true;
    state.activeItem = item;
    state.activeItemId = item.id;
    state.canDrag = false;
    container.style.cursor = "auto";

    const imgSrc = item.querySelector("img").src;
    const imgMatch = imgSrc.match(/\/img(\d+)\.jpg/);
    const imgNum = imgMatch ? parseInt(imgMatch[1]) : 1;
    const titleIndex = (imgNum - 1) % items.length;

    setAndAnimateTitle(items[titleIndex]);
    item.style.visibility = "hidden";

    const rect = item.getBoundingClientRect();
    const targetImg = item.querySelector("img").src;

    state.originalPosition = {
      id: item.id,
      rect: rect,
      imgSrc: targetImg,
    };

    overlay.classList.add("active");

    const expandedItem = document.createElement("div");
    expandedItem.className = "expanded-item";
    expandedItem.style.width = `${itemWidth}px`;
    expandedItem.style.height = `${itemHeight}px`;

    const img = document.createElement("img");
    img.src = targetImg;
    expandedItem.appendChild(img);
    expandedItem.addEventListener("click", closeExpandedItem);
    document.body.appendChild(expandedItem);

    state.expandedItem = expandedItem;

    document.querySelectorAll(".item").forEach((el) => {
      if (el !== state.activeItem) {
        gsap.to(el, {
          opacity: 0,
          duration: 0.3,
          ease: "power2.out",
        });
      }
    });

    const viewportWidth = window.innerWidth;
    const isMobile = window.innerWidth <= 1000;
    const targetWidth = viewportWidth * (isMobile ? 0.75 : 0.4);
    const targetHeight = targetWidth * 1.2;

    gsap.delayedCall(0.5, animateTitleIn);

    gsap.fromTo(
      expandedItem,
      {
        width: itemWidth,
        height: itemHeight,
        x: rect.left + itemWidth / 2 - window.innerWidth / 2,
        y: rect.top + itemHeight / 2 - window.innerHeight / 2,
      },
      {
        width: targetWidth,
        height: targetHeight,
        x: 0,
        y: 0,
        duration: 1,
        ease: "hop",
      }
    );
  };

  const closeExpandedItem = () => {
    const state = stateRef.current;
    const container = containerRef.current;
    const overlay = overlayRef.current;

    if (!state.expandedItem || !state.originalPosition) return;

    animateTitleOut();
    overlay.classList.remove("active");
    const originalRect = state.originalPosition.rect;

    document.querySelectorAll(".item").forEach((el) => {
      if (el.id !== state.activeItemId) {
        gsap.to(el, {
          opacity: 1,
          duration: 0.5,
          delay: 0.5,
          ease: "power2.out",
        });
      }
    });

    const originalItem = document.getElementById(state.activeItemId);

    gsap.to(state.expandedItem, {
      width: itemWidth,
      height: itemHeight,
      x: originalRect.left + itemWidth / 2 - window.innerWidth / 2,
      y: originalRect.top + itemHeight / 2 - window.innerHeight / 2,
      duration: 1,
      ease: "hop",
      onComplete: () => {
        if (state.expandedItem && state.expandedItem.parentNode) {
          document.body.removeChild(state.expandedItem);
        }

        if (originalItem) {
          originalItem.style.visibility = "visible";
        }

        state.expandedItem = null;
        state.isExpanded = false;
        state.activeItem = null;
        state.originalPosition = null;
        state.activeItemId = null;
        state.canDrag = true;
        container.style.cursor = "grab";
        state.dragVelocityX = 0;
        state.dragVelocityY = 0;
      },
    });
  };

  const animate = () => {
    const state = stateRef.current;
    const canvas = canvasRef.current;

    if (!canvas) return;

    if (state.canDrag) {
      const ease = 0.085;
      state.currentX += (state.targetX - state.currentX) * ease;
      state.currentY += (state.targetY - state.currentY) * ease;

      canvas.style.transform = `translate3d(${state.currentX}px, ${state.currentY}px, 0)`;

      const now = Date.now();
      const distMoved = Math.sqrt(
        Math.pow(state.currentX - state.lastX, 2) +
          Math.pow(state.currentY - state.lastY, 2)
      );

      const isMobile = window.innerWidth <= 1000;
      const updateThreshold = isMobile ? 100 : 80;
      const updateInterval = isMobile ? 150 : 100;

      if (
        distMoved > updateThreshold ||
        now - state.lastUpdateTime > updateInterval
      ) {
        updateVisibleItems();
        state.lastX = state.currentX;
        state.lastY = state.currentY;
        state.lastUpdateTime = now;
      }
    }

    state.animationFrameId = requestAnimationFrame(animate);
  };

  const handleMouseDown = (e) => {
    const state = stateRef.current;

    if (!state.canDrag) return;
    state.isDragging = true;
    state.mouseHasMoved = false;
    state.startX = e.clientX;
    state.startY = e.clientY;
    containerRef.current.style.cursor = "grabbing";
  };

  const handleMouseMove = (e) => {
    const state = stateRef.current;

    if (!state.isDragging || !state.canDrag) return;

    const dx = e.clientX - state.startX;
    const dy = e.clientY - state.startY;

    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
      state.mouseHasMoved = true;
    }

    const now = Date.now();
    const dt = Math.max(10, now - state.lastDragTime);
    state.lastDragTime = now;

    state.dragVelocityX = dx / dt;
    state.dragVelocityY = dy / dt;

    state.targetX += dx;
    state.targetY += dy;

    state.startX = e.clientX;
    state.startY = e.clientY;
  };

  const handleMouseUp = (e) => {
    const state = stateRef.current;

    if (!state.isDragging) return;
    state.isDragging = false;

    if (state.canDrag) {
      containerRef.current.style.cursor = "grab";

      if (
        Math.abs(state.dragVelocityX) > 0.1 ||
        Math.abs(state.dragVelocityY) > 0.1
      ) {
        const momentumFactor = 200;
        state.targetX += state.dragVelocityX * momentumFactor;
        state.targetY += state.dragVelocityY * momentumFactor;
      }
    }
  };

  const handleTouchStart = (e) => {
    const state = stateRef.current;

    if (!state.canDrag) return;
    state.isDragging = true;
    state.mouseHasMoved = false;
    state.startX = e.touches[0].clientX;
    state.startY = e.touches[0].clientY;
  };

  const handleTouchMove = (e) => {
    const state = stateRef.current;

    if (!state.isDragging || !state.canDrag) return;

    const dx = e.touches[0].clientX - state.startX;
    const dy = e.touches[0].clientY - state.startY;

    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
      state.mouseHasMoved = true;
    }

    const sensitivityMultiplier = 1.5;
    state.targetX += dx * sensitivityMultiplier;
    state.targetY += dy * sensitivityMultiplier;

    state.startX = e.touches[0].clientX;
    state.startY = e.touches[0].clientY;
  };

  const handleTouchEnd = () => {
    stateRef.current.isDragging = false;
  };

  const handleOverlayClick = () => {
    if (stateRef.current.isExpanded) closeExpandedItem();
  };

  const handleResize = () => {
    const state = stateRef.current;

    if (state.isExpanded && state.expandedItem) {
      const viewportWidth = window.innerWidth;
      const isMobile = window.innerWidth <= 768;
      const targetWidth = viewportWidth * (isMobile ? 0.6 : 0.4);
      const targetHeight = targetWidth * 1.2;

      gsap.to(state.expandedItem, {
        width: targetWidth,
        height: targetHeight,
        duration: 0.3,
        ease: "power2.out",
      });
    } else {
      updateVisibleItems();
    }
  };

  const initializeGallery = () => {
    const container = containerRef.current;
    const overlay = overlayRef.current;

    if (!container || !overlay) return;

    if (stateRef.current.animationFrameId) {
      cancelAnimationFrame(stateRef.current.animationFrameId);
      stateRef.current.animationFrameId = null;
    }

    container.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    container.addEventListener("touchstart", handleTouchStart, {
      passive: true,
    });
    window.addEventListener("touchmove", handleTouchMove, { passive: true });
    window.addEventListener("touchend", handleTouchEnd);
    window.addEventListener("resize", handleResize);
    overlay.addEventListener("click", handleOverlayClick);

    updateVisibleItems();

    if (!stateRef.current.animationFrameId) {
      animate();
    }
  };

  return (
    <>
      <div className="gallery-container" ref={containerRef}>
        <div className="canvas" id="canvas" ref={canvasRef}></div>
        <div className="overlay" id="overlay" ref={overlayRef}></div>
      </div>
      <div className="project-title" ref={projectTitleRef}>
        <p></p>
      </div>
    </>
  );
}
