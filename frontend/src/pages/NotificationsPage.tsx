import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { getApiErrorMessage } from "../services/auth";
import {
  getNotifications,
  markNotificationRead,
  type InAppNotification,
} from "../services/student";
import "./StudentPages.css";

interface NotificationRequest {
  ownerId: string;
  notifications: InAppNotification[];
  error: string;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function NotificationsPage() {
  const { user } = useAuth();
  const [request, setRequest] = useState<NotificationRequest | null>(null);
  const [updating, setUpdating] = useState<number | null>(null);
  const ownerId = user ? String(user.id) : null;
  const isCurrentRequest = ownerId !== null && request?.ownerId === ownerId;
  const notifications = isCurrentRequest ? request.notifications : [];
  const error = isCurrentRequest ? request.error : "";
  const loading = ownerId !== null && !isCurrentRequest;

  const loadNotifications = useCallback(async () => {
    if (ownerId === null) return;
    try {
      const response = await getNotifications();
      setRequest({
        ownerId,
        notifications: response.results,
        error: "",
      });
    } catch (requestError) {
      setRequest({
        ownerId,
        notifications: [],
        error: getApiErrorMessage(requestError),
      });
    }
  }, [ownerId]);

  useEffect(() => {
    if (ownerId === null) return;
    void loadNotifications();
  }, [ownerId, loadNotifications]);

  async function handleMarkRead(notification: InAppNotification) {
    if (notification.read_at) return;
    setUpdating(notification.id);
    try {
      const updated = await markNotificationRead(notification.id);
      setRequest((current) => {
        if (!current || current.ownerId !== ownerId) return current;
        return {
          ...current,
          notifications: current.notifications.map((item) =>
            item.id === updated.id ? updated : item
          ),
        };
      });
    } catch (requestError) {
      setRequest((current) => current && current.ownerId === ownerId
        ? { ...current, error: getApiErrorMessage(requestError) }
        : current
      );
    } finally {
      setUpdating(null);
    }
  }

  if (!user) {
    return (
      <main className="student-page">
        <h1>Notifications</h1>
        <p>Sign in to view your notifications.</p>
        <Link to="/login">Sign in</Link>
      </main>
    );
  }

  const unreadCount = notifications.filter((notification) => !notification.read_at).length;

  return (
    <main className="student-page">
      <header className="student-page-header">
        <div>
          <p className="student-eyebrow">NEXUS CAREER</p>
          <h1>Notifications</h1>
          <p className="student-muted">
            {unreadCount === 0 ? "You're all caught up." : unreadCount + " unread notification(s)"}
          </p>
        </div>
        <button className="student-secondary-button" type="button" onClick={() => void loadNotifications()}>
          Refresh
        </button>
      </header>
      {error && <div className="student-alert error" role="alert">{error}</div>}
      {loading ? (
        <div className="student-panel student-state">Loading notifications…</div>
      ) : notifications.length === 0 ? (
        <section className="student-panel student-empty">
          <h2>No notifications yet</h2>
          <p>Updates about your applications will appear here.</p>
          <Link className="student-primary-button" to="/opportunities">Browse opportunities</Link>
        </section>
      ) : (
        <div className="student-application-list">
          {notifications.map((notification) => (
            <article
              className={"student-panel student-notification-card" + (notification.read_at ? "" : " unread")}
              key={notification.id}
            >
              <div className="student-application-heading">
                <div>
                  <h2>{notification.title}</h2>
                  <p className="student-muted">{notification.message}</p>
                  <time className="student-muted">{formatDate(notification.created_at)}</time>
                </div>
                {!notification.read_at && <span className="student-status">Unread</span>}
              </div>
              <div className="student-actions">
                {notification.application_id && (
                  <Link to="/applications">View my application</Link>
                )}
                {notification.referral_request_id && (
                  <Link to={user.role === "ALUMNI" ? "/alumni/referrals" : "/referrals"}>
                    View referral request
                  </Link>
                )}
                {!notification.read_at && (
                  <button
                    className="student-secondary-button"
                    type="button"
                    disabled={updating === notification.id}
                    onClick={() => void handleMarkRead(notification)}
                  >
                    {updating === notification.id ? "Updating…" : "Mark as read"}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
