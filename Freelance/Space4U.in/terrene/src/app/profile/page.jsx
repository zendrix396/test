"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useUser } from "@/lib/hooks";
import fetchApi from "@/lib/api";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { FiCamera, FiTrash2 } from "react-icons/fi";
import { useViewTransition } from "@/hooks/useViewTransition";
import "./profile.css";

const UserRankingDisplay = ({ user }) => {
  const [rank, setRank] = useState(null);
  const { navigateWithTransition } = useViewTransition();

  useEffect(() => {
    const fetchRank = async () => {
      if (!user) return;
      try {
        const leaderboard = await fetchApi("/auth/leaderboard/");
        if (leaderboard && Array.isArray(leaderboard)) {
          const userEntry = leaderboard.find(u => u.username === user.username);
          if (userEntry) {
            setRank(userEntry.rank);
          }
        }
      } catch (error) {
        console.error("Failed to fetch ranking:", error);
      }
    };
    fetchRank();
  }, [user]);

  if (!rank) return null;

  return (
    <div style={{ margin: '0.5rem 0' }}>
      <a
        href="/leaderboard"
        onClick={(e) => {
          e.preventDefault();
          navigateWithTransition("/leaderboard");
        }}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          color: 'var(--base-200)',
          textDecoration: 'none',
          fontSize: '0.95rem',
          fontWeight: 600,
          transition: 'color 0.25s ease'
        }}
        onMouseEnter={(e) => e.target.style.color = 'var(--base-100)'}
        onMouseLeave={(e) => e.target.style.color = 'var(--base-200)'}
      >
        Rank #{rank} →
      </a>
    </div>
  );
};

const ProfilePage = () => {
  const { navigateWithTransition } = useViewTransition();
  const { user, isLoading, mutate } = useUser();

  const heroRef = useRef(null);
  const statsRef = useRef(null);

  const [form, setForm] = useState({
    username: "",
    display_name: "",
    first_name: "",
    last_name: "",
    phone_number: "",
    bio: "",
  });
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [avatarFile, setAvatarFile] = useState(null);
  const [removeAvatar, setRemoveAvatar] = useState(false);
  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [status, setStatus] = useState({ type: null, message: "" });
  const [isSaving, setIsSaving] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [referralCode, setReferralCode] = useState(null);
  const [referralCount, setReferralCount] = useState(0);
  const [referralLink, setReferralLink] = useState("");
  const [isLoadingReferral, setIsLoadingReferral] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      navigateWithTransition("/login");
    }
  }, [user, isLoading, navigateWithTransition]);

  useEffect(() => {
    if (!user) return;
    setForm({
      username: user.username || "",
      display_name: user.display_name || "",
      first_name: user.first_name || "",
      last_name: user.last_name || "",
      phone_number: user.phone_number || "",
      bio: user.bio || "",
    });
    setAvatarPreview(user.profile_image_url || null);
    setAvatarFile(null);
    setRemoveAvatar(false);
  }, [user]);

  useEffect(() => {
    if (!user) return;
    const loadOrders = async () => {
      setOrdersLoading(true);
      try {
        const data = await fetchApi("/commerce/orders/");
        setOrders(Array.isArray(data) ? data.slice(0, 6) : []);
      } catch (error) {
        console.error("Failed to fetch orders", error);
      } finally {
        setOrdersLoading(false);
      }
    };
    loadOrders();
  }, [user]);

  useEffect(() => {
    if (!user) return;
    const loadReferral = async () => {
      setIsLoadingReferral(true);
      try {
        const data = await fetchApi("/auth/referral-code/");
        setReferralCode(data.code);
        setReferralLink(data.referral_link || `${typeof window !== 'undefined' ? window.location.origin : ''}/signup?ref=${data.code}`);
        // Try to get referral count
        try {
          const referralData = await fetchApi("/auth/referrals/");
          setReferralCount(referralData.referrals || 0);
        } catch (e) {
          // Ignore if endpoint doesn't exist
        }
      } catch (error) {
        console.error("Failed to load referral code", error);
      } finally {
        setIsLoadingReferral(false);
      }
    };
    loadReferral();
  }, [user]);

  useGSAP(
    () => {
      if (heroRef.current) {
        gsap.fromTo(
          heroRef.current.querySelectorAll(".profile-hero .reveal"),
          { y: 40, opacity: 0 },
          { y: 0, opacity: 1, duration: 1, stagger: 0.12, ease: "power3.out" }
        );
      }
      if (statsRef.current) {
        gsap.fromTo(
          statsRef.current.querySelectorAll(".profile-stat-card"),
          { y: 35, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.9, stagger: 0.1, ease: "power3.out", delay: 0.2 }
        );
      }
    },
    { scope: heroRef }
  );

  const orderStats = useMemo(() => {
    return user?.order_stats || {
      total_orders: 0,
      completed_orders: 0,
      open_orders: 0,
      total_spent: "0.00",
    };
  }, [user]);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleAvatarChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    setRemoveAvatar(false);
    const objectUrl = URL.createObjectURL(file);
    setAvatarPreview(objectUrl);
  };

  useEffect(() => {
    return () => {
      if (avatarPreview && avatarPreview.startsWith("blob:")) {
        URL.revokeObjectURL(avatarPreview);
      }
    };
  }, [avatarPreview]);

  const handleRemoveAvatar = () => {
    setAvatarFile(null);
    if (avatarPreview && avatarPreview.startsWith("blob:")) {
      URL.revokeObjectURL(avatarPreview);
    }
    setAvatarPreview(null);
    setRemoveAvatar(true);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!user || isSaving) return;

    setStatus({ type: null, message: "" });

    try {
      setIsSaving(true);
      const body = new FormData();
      Object.entries(form).forEach(([key, value]) => {
        body.append(key, value ?? "");
      });
      if (avatarFile) {
        body.append("profile_image", avatarFile);
      }
      if (removeAvatar) {
        body.append("remove_profile_image", "true");
      }

      const updated = await fetchApi("/auth/me/", {
        method: "PATCH",
        body,
      });

      mutate(updated);
      setStatus({ type: "success", message: "Profile updated successfully." });
      setTimeout(() => {
        setShowEditForm(false);
      }, 500);
    } catch (error) {
      setStatus({
        type: "error",
        message: error?.message || "We couldn't update your profile. Please try again.",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const initials = useMemo(() => {
    if (!user?.username) return "S4";
    return user.username
      .split(" ")
      .map((part) => part.charAt(0).toUpperCase())
      .join("")
      .slice(0, 2);
  }, [user]);

  return (
    <>
      <div className="page profile-page">
        <div className="container profile-wrapper" ref={heroRef}>
          <section className="profile-hero">
            <div>
              <h1 className="reveal">Command Center</h1>
              <p className="lead reveal">
                Manage your identity, monitor loyalty ranks, and keep a pulse on every parcel hurtling toward your doorstep.
              </p>
              <div className="profile-grid reveal" ref={statsRef}>
                <article className="profile-stat-card">
                  <span className="label">Loyalty Points</span>
                  <h3>{user?.loyalty_points ?? 0}</h3>
                  <UserRankingDisplay user={user} />
                  <p>Unlock exclusive drops and leaderboard boosts.</p>
                </article>
                <article className="profile-stat-card">
                  <span className="label">Wallet Balance</span>
                  <h3>₹{user?.wallet_balance ?? "0.00"}</h3>
                  <p>Instant credits waiting to be deployed.</p>
                </article>
                <article className="profile-stat-card">
                  <span className="label">Total Orders</span>
                  <h3>{orderStats.total_orders}</h3>
                  <p>{orderStats.completed_orders} completed · {orderStats.open_orders} in progress</p>
                </article>
                <article className="profile-stat-card">
                  <span className="label">Total Spent</span>
                  <h3>₹{orderStats.total_spent}</h3>
                  <p>Across every fandom conquest to date.</p>
                </article>
              </div>
            </div>
            <div className="profile-avatar-section reveal">
              <div className="profile-avatar">
                {avatarPreview ? (
                  <img src={avatarPreview} alt="Profile avatar" />
                ) : (
                  <div className="avatar-fallback">{initials}</div>
                )}
              </div>
              <div className="profile-avatar-info">
                <p className="profile-username">@{user?.username || "username"}</p>
                {user?.bio && <p className="profile-bio">{user.bio}</p>}
                <button
                  type="button"
                  className="profile-edit-button"
                  onClick={() => setShowEditForm(!showEditForm)}
                >
                  {showEditForm ? "Cancel" : "Edit profile"}
                </button>
                {referralCode && (
                  <div className="profile-referral-compact">
                    <div className="profile-referral-compact-header">
                      <span>Refer to Friend</span>
                    </div>
                    <div className="profile-referral-compact-content">
                      <div className="profile-referral-compact-item">
                        <input
                          type="text"
                          readOnly
                          value={referralCode}
                          onClick={(e) => e.target.select()}
                          className="profile-referral-compact-input"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(referralCode);
                            setStatus({ type: "success", message: "Code copied!" });
                          }}
                          className="profile-referral-compact-button"
                        >
                          Copy
                        </button>
                      </div>
                      <div className="profile-referral-compact-item">
                        <input
                          type="text"
                          readOnly
                          value={referralLink}
                          onClick={(e) => e.target.select()}
                          className="profile-referral-compact-input"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(referralLink);
                            setStatus({ type: "success", message: "Link copied!" });
                          }}
                          className="profile-referral-compact-button"
                        >
                          Copy
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          {showEditForm && (
          <section className="profile-card">
            <header>
              <div>
                <h2>Edit profile</h2>
                <p style={{ color: "rgba(255, 255, 255, 0.6)" }}>
                  Update your storefront persona. Your email stays locked for security.
                </p>
              </div>
            </header>

            <form className="profile-form" onSubmit={handleSubmit}>
              <label>
                Username
                <input
                  name="username"
                  value={form.username}
                  onChange={handleInputChange}
                  placeholder="Enter username"
                  required
                />
              </label>
              <label>
                Display name
                <input
                  name="display_name"
                  value={form.display_name}
                  onChange={handleInputChange}
                  placeholder="Name visible across the community"
                />
              </label>
              <label>
                First name
                <input
                  name="first_name"
                  value={form.first_name}
                  onChange={handleInputChange}
                  placeholder="Given name"
                />
              </label>
              <label>
                Last name
                <input
                  name="last_name"
                  value={form.last_name}
                  onChange={handleInputChange}
                  placeholder="Family name"
                />
              </label>
              <label>
                Phone number
                <input
                  name="phone_number"
                  value={form.phone_number}
                  onChange={handleInputChange}
                  placeholder="Include country code (+91…)"
                />
              </label>
              <label className="full-width">
                Bio / status
                <textarea
                  name="bio"
                  value={form.bio}
                  onChange={handleInputChange}
                  placeholder="Tell fellow collectors about your favourite saga or grail hunt."
                />
              </label>
              <div className="full-width profile-actions" style={{ justifyContent: "flex-start", gap: "1rem" }}>
                <label className="secondary" style={{ display: "inline-flex", alignItems: "center", gap: "0.6rem", cursor: "pointer" }}>
                  <FiCamera /> Upload new avatar
                  <input
                    type="file"
                    accept="image/*"
                    style={{ display: "none" }}
                    onChange={handleAvatarChange}
                  />
                </label>
                <button
                  type="button"
                  className="secondary"
                  onClick={handleRemoveAvatar}
                  disabled={(!avatarPreview && !user?.profile_image_url) || isSaving}
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.6rem" }}
                >
                  <FiTrash2 /> Remove avatar
                </button>
              </div>
              <div className="full-width profile-actions">
                {status.message && (
                  <span className={`profile-status ${status.type === "error" ? "is-error" : "is-success"}`}>
                    {status.message}
                  </span>
                )}
                <button type="submit" className="primary" disabled={isSaving}>
                  {isSaving ? "Saving changes…" : "Save changes"}
                </button>
                <button
                  type="button"
                  className="logout"
                  onClick={async () => {
                    if (typeof window !== "undefined") {
                      localStorage.removeItem("accessToken");
                      localStorage.removeItem("refreshToken");
                      mutate(null);
                      navigateWithTransition("/login");
                    }
                  }}
                >
                  Log out
                </button>
              </div>
            </form>
          </section>
          )}

          <section className="profile-card profile-orders">
            <header>
              <h2>Latest orders</h2>
              <a href="/orders" style={{ color: "rgba(242, 84, 91, 0.85)", fontWeight: 600 }}>
                View full timeline ↗
              </a>
            </header>
            {ordersLoading && <p>Fetching your mission logs…</p>}
            {!ordersLoading && orders.length === 0 && (
              <div className="profile-empty">No orders yet. Your first drop awaits!</div>
            )}
            {!ordersLoading && orders.length > 0 && (
              <div className="profile-orders-list">
                {orders.map((order) => {
                  const statusClass = order.status ? order.status.toLowerCase() : "";
                  return (
                    <article key={order.id} className="profile-orders-card">
                      <header>
                        <h3>Order #{order.id}</h3>
                        <span className={`order-status is-${statusClass}`}>{order.status?.replace(/_/g, " ")}</span>
                      </header>
                      <div>
                        <p style={{ color: "rgba(255, 255, 255, 0.75)" }}>
                          Total • ₹{order.total_payable || order.total_cost}
                        </p>
                        <p style={{ color: "rgba(255, 255, 255, 0.6)", fontSize: "0.9rem" }}>
                          Placed {order.created_at ? new Date(order.created_at).toLocaleString() : "recently"}
                        </p>
                      </div>
                      <footer>
                        <span>{order.payment_method || "N/A"}</span>
                        <a href="/orders" style={{ color: "rgba(242, 84, 91, 0.8)" }}>Track →</a>
                      </footer>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </>
  );
};

export default ProfilePage;
