import sys
import os
from kivy.utils import platform

# Desktop platform local notification fallback (Windows / macOS / Linux)
try:
    from plyer import notification
except Exception:
    notification = None


def request_notification_permissions():
    """Requests runtime permissions on Android 13+ (API 33+) and iOS."""
    if platform == 'android':
        try:
            from jnius import autoclass
            Build = autoclass('android.os.Build$VERSION')
            if Build.SDK_INT >= 33:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                ContextCompat = autoclass('androidx.core.content.ContextCompat')
                Manifest = autoclass('android.Manifest$permission')
                PackageManager = autoclass('android.content.pm.PackageManager')

                activity = PythonActivity.mActivity
                permission = Manifest.POST_NOTIFICATIONS

                if ContextCompat.checkSelfPermission(activity, permission) != PackageManager.PERMISSION_GRANTED:
                    ActivityCompat = autoclass('androidx.core.app.ActivityCompat')
                    ActivityCompat.requestPermissions(activity, [permission], 101)
        except Exception as e:
            print(f"[NOTIFICATION PERMISSION ERROR - ANDROID]: {e}")

    elif platform == 'ios':
        try:
            from pyobjus import autoclass
            UNUserNotificationCenter = autoclass('UNUserNotificationCenter')
            center = UNUserNotificationCenter.currentNotificationCenter()
            # Request authorization options: Alert (1) | Sound (2) | Badge (4) = 7
            center.requestAuthorizationWithOptions_completionHandler_(7, None)
        except Exception as e:
            print(f"[NOTIFICATION PERMISSION ERROR - IOS]: {e}")


def schedule_offline_reminders():
    """Schedules periodic offline reminders across Android, iOS, and Desktop platforms."""
    title = "Sabi Learners Reminder!"
    message = "Knowledge is power! Spend a few minutes sharpening your mind today."

    # ------------------ 1. ANDROID (AlarmManager via Pyjnius) ------------------
    if platform == 'android':
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            Intent = autoclass('android.content.Intent')
            PendingIntent = autoclass('android.app.PendingIntent')
            AlarmManager = autoclass('android.app.AlarmManager')
            System = autoclass('java.lang.System')

            activity = PythonActivity.mActivity
            alarm_manager = activity.getSystemService(Context.ALARM_SERVICE)

            # Pass PythonActivity directly
            intent = Intent(activity, PythonActivity)
            flags = PendingIntent.FLAG_UPDATE_CURRENT
            
            # PendingIntent FLAG_IMMUTABLE requirement for Android 12+
            try:
                FLAG_IMMUTABLE = PendingIntent.FLAG_IMMUTABLE
                flags |= FLAG_IMMUTABLE
            except Exception:
                pass

            pending_intent = PendingIntent.getActivity(activity, 1001, intent, flags)

            # Trigger every 24 hours (86,400,000 milliseconds)
            interval_ms = 24 * 60 * 60 * 1000
            trigger_at_ms = System.currentTimeMillis() + interval_ms

            alarm_manager.setInexactRepeating(
                AlarmManager.RTC_WAKEUP,
                trigger_at_ms,
                interval_ms,
                pending_intent
            )
            print("[NOTIFICATION MANAGER]: Android local offline alarm scheduled successfully.")
            return
        except Exception as e:
            print(f"[NOTIFICATION MANAGER ANDROID ERROR]: {e}")

    # ------------------ 2. IOS (UNUserNotificationCenter via Pyobjus) ------------------
    elif platform == 'ios':
        try:
            from pyobjus import autoclass, objc_str
            UNMutableNotificationContent = autoclass('UNMutableNotificationContent')
            UNTimeIntervalNotificationTrigger = autoclass('UNTimeIntervalNotificationTrigger')
            UNNotificationRequest = autoclass('UNNotificationRequest')
            UNUserNotificationCenter = autoclass('UNUserNotificationCenter')

            content = UNMutableNotificationContent.alloc().init()
            content.setTitle_(objc_str(title))
            content.setBody_(objc_str(message))

            # Schedule trigger every 24 hours (86,400 seconds)
            trigger = UNTimeIntervalNotificationTrigger.triggerWithTimeInterval_repeats_(86400, True)
            request = UNNotificationRequest.requestWithIdentifier_content_trigger_(
                objc_str("sabi_learners_daily_reminder"),
                content,
                trigger
            )

            center = UNUserNotificationCenter.currentNotificationCenter()
            center.addNotificationRequest_withCompletionHandler_(request, None)
            print("[NOTIFICATION MANAGER]: iOS local scheduled notification registered successfully.")
            return
        except Exception as e:
            print(f"[NOTIFICATION MANAGER IOS ERROR]: {e}")

    # ------------------ 3. DESKTOP (Windows, macOS, Linux Fallback) ------------------
    else:
        if notification:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Sabi Learners",
                    timeout=10
                )
                print("[NOTIFICATION MANAGER]: Desktop local test notification issued.")
            except Exception as e:
                print(f"[NOTIFICATION MANAGER DESKTOP ERROR]: {e}")


def init_offline_notifications():
    """Initializer entry point called when the application boots."""
    request_notification_permissions()
    schedule_offline_reminders()