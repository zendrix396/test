import React, { useEffect, useRef } from 'react';
import './SakuraPetals.css';

const SakuraPetals = () => {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const createPetal = () => {
      const petal = document.createElement('div');
      petal.classList.add('sakura-petal');
      
      // Randomize starting position and animation properties
      const startLeft = Math.random() * 100;
      const animationDuration = 5 + Math.random() * 5; // 5-10s
      const size = 10 + Math.random() * 10; // 10-20px
      
      petal.style.left = `${startLeft}%`;
      petal.style.animationDuration = `${animationDuration}s`;
      petal.style.width = `${size}px`;
      petal.style.height = `${size}px`;
      
      container.appendChild(petal);

      // Remove petal after animation
      setTimeout(() => {
        if (petal.parentNode === container) {
          container.removeChild(petal);
        }
      }, animationDuration * 1000);
    };

    const interval = setInterval(createPetal, 300); // Create a petal every 300ms

    return () => {
      clearInterval(interval);
      if (container) {
        container.innerHTML = '';
      }
    };
  }, []);

  return <div className="sakura-container" ref={containerRef} />;
};

export default SakuraPetals;

