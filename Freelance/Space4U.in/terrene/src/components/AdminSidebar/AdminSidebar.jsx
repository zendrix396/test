"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import fetchApi from "@/lib/api";
import "./AdminSidebar.css";

// A simple hook to fetch admin models
const useAdminModels = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const models = await fetchApi("/admin/metadata/models/");
        setData(models);
      } catch (e) {
        setError(e);
        console.error("Failed to fetch admin models:", e);
      }
    };

    fetchModels();
  }, []);

  return { models: data, error, isLoading: !data && !error };
};

const AdminSidebar = () => {
  const [isHovered, setIsHovered] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState({});
  const router = useRouter();
  const pathname = usePathname();
  const { models, isLoading } = useAdminModels();
  const sidebarContentRef = useRef(null);

  useEffect(() => {
    document.body.classList.toggle('admin-sidebar-hovered', isHovered);
    return () => {
      document.body.classList.remove('admin-sidebar-hovered');
    };
  }, [isHovered]);

  // Add scroll event listener directly to sidebar content
  useEffect(() => {
    const sidebarContent = sidebarContentRef.current;
    if (!sidebarContent) return;

    const handleWheel = (e) => {
      const { scrollTop, scrollHeight, clientHeight } = sidebarContent;
      const isAtTop = scrollTop <= 1;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 1;
      
      // If we're in the middle of the sidebar, stop propagation
      if (!isAtTop && !isAtBottom) {
        e.stopPropagation();
      } else if (isAtTop && e.deltaY < 0) {
        // At top and scrolling up - allow page scroll
      } else if (isAtBottom && e.deltaY > 0) {
        // At bottom and scrolling down - allow page scroll
      } else {
        // At boundaries but wrong direction - stop propagation
        e.stopPropagation();
      }
    };

    sidebarContent.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      sidebarContent.removeEventListener('wheel', handleWheel);
    };
  }, []);

  const toggleCategory = (appLabel) => {
    setExpandedCategories(prev => ({
      ...prev,
      [appLabel]: !prev[appLabel]
    }));
  };

  const handleItemClick = (path) => {
    router.push(path);
  };

  const getModelKeyFromPath = () => {
    const parts = pathname.split('/');
    if (parts.length >= 3 && parts[1] === 'admin') {
      return parts[2]; // e.g., 'user', 'order'
    }
    return null;
  };

  const currentModelKey = getModelKeyFromPath();

  // Prevent scroll propagation from sidebar to body
  const handleSidebarContentWheel = (e) => {
    const sidebarContent = e.currentTarget;
    const { scrollTop, scrollHeight, clientHeight } = sidebarContent;
    const isAtTop = scrollTop <= 1;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 1;
    
    // If we're in the middle of the sidebar (not at top and not at bottom)
    // Stop propagation so only sidebar scrolls, not the page
    if (!isAtTop && !isAtBottom) {
      // We're in the middle - sidebar can scroll, so stop propagation to body
      e.stopPropagation();
      // Don't prevent default - let the sidebar scroll naturally
    } else if (isAtTop && e.deltaY < 0) {
      // At top and scrolling up - allow to pass through to scroll page
      // Don't stop propagation
    } else if (isAtBottom && e.deltaY > 0) {
      // At bottom and scrolling down - allow to pass through to scroll page
      // Don't stop propagation
    } else {
      // At boundaries but wrong direction - stop propagation to keep scroll in sidebar
      e.stopPropagation();
    }
  };

  // Handle scroll on the sidebar container itself
  const handleSidebarWheel = (e) => {
    // Always stop scroll events on the sidebar container from reaching body
    e.stopPropagation();
  };

  return (
    <div
      className={`admin-sidebar ${isHovered ? 'hovered' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onWheel={handleSidebarWheel}
    >
      <div className="admin-sidebar-content" ref={sidebarContentRef} onWheel={handleSidebarContentWheel}>
        <div className="admin-sidebar-header">
          <h2>Terrene Admin</h2>
        </div>
        <nav className="admin-sidebar-nav">
          <div
            className={`admin-sidebar-item ${pathname === '/admin/dashboard' ? 'active' : ''}`}
            onClick={() => handleItemClick('/admin/dashboard')}
            role="link"
          >
            <span className="admin-sidebar-icon">📊</span>
            <span className="admin-sidebar-text">Dashboard</span>
          </div>

          {isLoading && <div className="admin-sidebar-item"><span className="admin-sidebar-text">Loading...</span></div>}
          {models?.map((app) => (
            <div key={app.app_label} className="admin-sidebar-category">
              <div
                className="admin-sidebar-category-header"
                onClick={() => toggleCategory(app.app_label)}
                role="button"
              >
                <span className="admin-sidebar-icon">📁</span>
                <span className="admin-sidebar-text">{app.name}</span>
                <span className={`admin-sidebar-arrow ${expandedCategories[app.app_label] ? 'expanded' : ''}`}>
                  ▼
                </span>
              </div>
              <div
                className={`admin-sidebar-category-items ${expandedCategories[app.app_label] ? 'expanded' : ''}`}
              >
                {app.models.map((model) => {
                  const modelKey = model.model_key || model.object_name.toLowerCase();
                  const path = `/admin/${modelKey}`;
                  return (
                    <div
                      key={model.object_name}
                      className={`admin-sidebar-item admin-sidebar-subitem ${currentModelKey === modelKey ? 'active' : ''}`}
                      onClick={() => handleItemClick(path)}
                      role="link"
                    >
                      <span className="admin-sidebar-text">{model.name}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>
    </div>
  );
};

export default AdminSidebar;
