"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import fetchApi from "@/lib/api";
import AdminSidebar from "@/components/AdminSidebar/AdminSidebar";
import "../admin.css";
import "./model-page.css";

// Helper function to format display names
const formatColumnName = (key) => {
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Main Page Component
const AdminModelPage = () => {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();

  const modelPath = params.model || [];
  const modelKey = modelPath[0];
  const action = modelPath[1]; // 'add' or an ID
  const subAction = modelPath[2]; // 'edit'

  const [user, setUser] = useState(null);
  const [modelConfig, setModelConfig] = useState(null);

  // Determine current mode
  const mode = (() => {
    if (action === 'add') return 'add';
    if (action && subAction === 'edit') return 'edit';
    if (action) return 'detail';
    return 'list';
  })();

  const itemId = (mode === 'detail' || mode === 'edit') ? action : null;

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
          router.push("/admin");
          return;
        }
        const check = await fetchApi("/admin/check-superuser/");
        if (!check.is_superuser) {
          router.push("/admin");
          return;
        }
        setUser(check);
      } catch (e) {
        router.push("/admin");
      }
    };
    checkAuth();
  }, [router]);

  useEffect(() => {
    if (user && modelKey) {
      const fetchConfig = async () => {
        try {
          // Try to determine app_label from model_key
          // This is a simplified approach - in production you'd want a better mapping
          let app_label = 'commerce'; // default
          if (['user', 'badge', 'loyalty', 'referral', 'wallet'].some(k => modelKey.includes(k))) {
            app_label = 'users';
          } else if (['product', 'category', 'batch', 'variant', 'stock'].some(k => modelKey.includes(k))) {
            app_label = 'products';
          } else if (['shipment', 'warehouse', 'waybill'].some(k => modelKey.includes(k))) {
            app_label = 'shipping';
          } else if (['group'].includes(modelKey)) {
            app_label = 'auth';
          }

          // Get model name from model_key - convert to proper case
          const modelName = modelKey.charAt(0).toUpperCase() + modelKey.slice(1);
          // Handle special cases
          const modelNameMap = {
            'user': 'CustomUser',
            'order': 'Order',
            'product': 'Product',
            'category': 'Category',
            'cart': 'Cart',
            'coupon': 'Coupon',
          };
          const finalModelName = modelNameMap[modelKey] || modelName;

          const data = await fetchApi(`/admin/metadata/config/${app_label}/${finalModelName}/`);
          setModelConfig(data);
        } catch (e) {
          console.error("Failed to load model config:", e);
          // Continue without config - will use defaults
        }
      };
      fetchConfig();
    }
  }, [user, modelKey]);

  if (!user || !modelKey) {
    return (
      <div className="admin-model-page">
        <AdminSidebar />
        <main className="admin-main-content">
          <div className="admin-dashboard-loading"><p>Authenticating...</p></div>
        </main>
      </div>
    );
  }

  return (
    <div className="admin-model-page">
      <AdminSidebar />
      <main className="admin-main-content">
        <div className="admin-model-content">
          {mode === 'list' && <ModelListPage modelKey={modelKey} modelConfig={modelConfig} />}
          {(mode === 'detail' || mode === 'edit') && (
            <ModelDetailPage
              modelKey={modelKey}
              itemId={itemId}
              isEditingDefault={mode === 'edit'}
              modelConfig={modelConfig}
            />
          )}
          {mode === 'add' && <ModelAddPage modelKey={modelKey} modelConfig={modelConfig} />}
        </div>
      </main>
    </div>
  );
};

// List Page Component
const ModelListPage = ({ modelKey, modelConfig }) => {
  const router = useRouter();
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");

  // Use modelConfig list_display if available, otherwise use defaults
  const displayColumns = modelConfig?.list_display || ['id', 'name', 'email', 'status', 'created_at'];

  useEffect(() => {
    const loadItems = async () => {
      setIsLoading(true);
      const params = new URLSearchParams({ page: page.toString(), page_size: '50' });
      if (search) params.append('search', search);
      try {
        const data = await fetchApi(`/admin/api/${modelKey}/?${params}`);
        setItems(data.results || []);
        setTotal(data.total || 0);
      } catch (e) {
        console.error("Failed to load items:", e);
      } finally {
        setIsLoading(false);
      }
    };
    loadItems();
  }, [modelKey, page, search]);

  const handleRowClick = (item) => {
    router.push(`/admin/${modelKey}/${item.id}`);
  };

  return (
    <>
      <div className="admin-model-header">
        <h1>{formatColumnName(modelKey)}s</h1>
        <button onClick={() => router.push(`/admin/${modelKey}/add`)} className="admin-action-btn">
          Add {formatColumnName(modelKey)}
        </button>
      </div>
      <div className="admin-model-filters">
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="admin-search-input"
        />
      </div>
      <div className="admin-section-card">
        <div className="admin-table-container">
          {isLoading ? (
            <p>Loading...</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  {displayColumns.map((key) => (
                    <th key={key}>{formatColumnName(key)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={displayColumns.length} style={{ textAlign: 'center', padding: '2rem' }}>
                      No items found
                    </td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr key={item.id} onClick={() => handleRowClick(item)} style={{ cursor: 'pointer' }}>
                      {displayColumns.map((key) => (
                        <td key={key}>{String(item[key] ?? '—')}</td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
      <div className="admin-pagination">
        <button
          className="admin-action-btn"
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page === 1}
        >
          Previous
        </button>
        <span>Page {page} of {Math.ceil(total / 50)}</span>
        <button
          className="admin-action-btn"
          onClick={() => setPage(page + 1)}
          disabled={page >= Math.ceil(total / 50)}
        >
          Next
        </button>
      </div>
    </>
  );
};

// Detail / Edit Page Component
const ModelDetailPage = ({ modelKey, itemId, isEditingDefault = false, modelConfig }) => {
  const router = useRouter();
  const [item, setItem] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(isEditingDefault);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const loadItem = async () => {
      setIsLoading(true);
      try {
        const data = await fetchApi(`/admin/api/${modelKey}/${itemId}/`);
        setItem(data);
      } catch (e) {
        console.error("Failed to load item:", e);
      } finally {
        setIsLoading(false);
      }
    };
    loadItem();
  }, [modelKey, itemId]);

  const handleSave = async (formData) => {
    setIsSaving(true);
    try {
      await fetchApi(`/admin/api/${modelKey}/${itemId}/`, {
        method: 'PATCH',
        body: JSON.stringify(formData),
      });
      router.push(`/admin/${modelKey}/${itemId}`); // Go back to detail view
      setIsEditing(false);
    } catch (e) {
      alert("Failed to save.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) return <div className="admin-dashboard-loading"><p>Loading Item...</p></div>;
  if (!item) return <p>Item not found.</p>;

  return (
    <>
      <div className="admin-model-header">
        <h1>
          {isEditing ? 'Edit' : 'View'} {formatColumnName(modelKey)} #{itemId}
        </h1>
        <div>
          {!isEditing && (
            <button onClick={() => router.push(`/admin/${modelKey}/${itemId}/edit`)} className="admin-action-btn">
              Edit
            </button>
          )}
          <button onClick={() => router.push(`/admin/${modelKey}`)} className="admin-back-btn">
            ← Back to List
          </button>
        </div>
      </div>
      {isEditing ? (
        <ModelForm
          item={item}
          onSave={handleSave}
          onCancel={() => router.push(`/admin/${modelKey}/${itemId}`)}
          isSaving={isSaving}
          modelConfig={modelConfig}
        />
      ) : (
        <div className="admin-model-detail">
          {Object.entries(item).map(([key, value]) => (
            <div key={key} className="admin-detail-item">
              <label>{formatColumnName(key)}</label>
              <div>{String(value ?? '—')}</div>
            </div>
          ))}
        </div>
      )}
    </>
  );
};

// Add New Page Component
const ModelAddPage = ({ modelKey, modelConfig }) => {
  const router = useRouter();
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async (formData) => {
    setIsSaving(true);
    try {
      const newItem = await fetchApi(`/admin/api/${modelKey}/`, {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      // Redirect to the new item's detail page
      router.push(`/admin/${modelKey}/${newItem.id}`);
    } catch (e) {
      alert("Failed to create item.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <div className="admin-model-header">
        <h1>Add New {formatColumnName(modelKey)}</h1>
        <button onClick={() => router.push(`/admin/${modelKey}`)} className="admin-back-btn">
          ← Cancel
        </button>
      </div>
      <ModelForm
        item={{}}
        onSave={handleSave}
        onCancel={() => router.push(`/admin/${modelKey}`)}
        isSaving={isSaving}
        modelConfig={modelConfig}
      />
    </>
  );
};

// Reusable Form Component
const ModelForm = ({ item, onSave, onCancel, isSaving, modelConfig }) => {
  const [formData, setFormData] = useState(item);

  useEffect(() => {
    setFormData(item);
  }, [item]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const { id, created_at, updated_at, ...submitData } = formData;
    onSave(submitData);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  // Get fields from modelConfig if available, otherwise use item keys
  const fields = modelConfig?.form_fields || Object.keys(formData).filter(
    (key) => !['id', 'created_at', 'updated_at'].includes(key)
  );

  return (
    <form onSubmit={handleSubmit} className="admin-model-form">
      {fields.map((field) => {
        const fieldName = typeof field === 'string' ? field : field.name;
        const fieldInfo = typeof field === 'object' ? field : null;
        const value = formData[fieldName];
        const fieldType = fieldInfo?.field_type || (typeof value === 'boolean' ? 'checkbox' : 'text');

        return (
          <div key={fieldName} className="admin-form-field">
            <label>{fieldInfo?.label || formatColumnName(fieldName)}</label>
            {fieldType === 'checkbox' ? (
              <input
                name={fieldName}
                type="checkbox"
                checked={value || false}
                onChange={handleChange}
                className="admin-form-input"
              />
            ) : fieldType === 'textarea' ? (
              <textarea
                name={fieldName}
                value={value ?? ''}
                onChange={handleChange}
                className="admin-form-input"
                rows={4}
              />
            ) : (
              <input
                name={fieldName}
                type={fieldType === 'datetime' ? 'datetime-local' : fieldType === 'number' ? 'number' : 'text'}
                value={value ?? ''}
                onChange={handleChange}
                className="admin-form-input"
                placeholder={`Enter ${formatColumnName(fieldName).toLowerCase()}`}
              />
            )}
          </div>
        );
      })}
      <div className="admin-form-actions">
        <button type="submit" disabled={isSaving} className="admin-action-btn">
          {isSaving ? 'Saving...' : 'Save'}
        </button>
        <button type="button" onClick={onCancel} className="admin-action-btn">
          Cancel
        </button>
      </div>
    </form>
  );
};

export default AdminModelPage;
