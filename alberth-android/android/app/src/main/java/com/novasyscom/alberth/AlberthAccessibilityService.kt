package com.novasyscom.alberth

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.os.Build
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject

class AlberthAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "AlberthAccessibility"
        var instance: AlberthAccessibilityService? = null
            private set

        fun isRunning(): Boolean = instance != null
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.i(TAG, "AlberthAccessibilityService connected and ready")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Listening to UI changes if needed
    }

    override fun onInterrupt() {
        Log.w(TAG, "AlberthAccessibilityService interrupted")
    }

    override fun onDestroy() {
        if (instance == this) {
            instance = null
        }
        super.onDestroy()
        Log.i(TAG, "AlberthAccessibilityService destroyed")
    }

    /**
     * Dispatches a tap gesture at the specified screen coordinates (x, y).
     */
    fun performClick(x: Float, y: Float, callback: (Boolean) -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            callback(false)
            return
        }

        val path = Path().apply {
            moveTo(x, y)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, 100)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()

        dispatchGesture(gesture, object : GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                Log.d(TAG, "Click gesture succeeded at ($x, $y)")
                callback(true)
            }

            override fun onCancelled(gestureDescription: GestureDescription?) {
                Log.w(TAG, "Click gesture cancelled at ($x, $y)")
                callback(false)
            }
        }, null)
    }

    /**
     * Dispatches a swipe gesture from (x1, y1) to (x2, y2) over durationMs.
     */
    fun performSwipe(x1: Float, y1: Float, x2: Float, y2: Float, durationMs: Long, callback: (Boolean) -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            callback(false)
            return
        }

        val path = Path().apply {
            moveTo(x1, y1)
            lineTo(x2, y2)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, maxOf(100L, durationMs))
        val gesture = GestureDescription.Builder().addStroke(stroke).build()

        dispatchGesture(gesture, object : GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                Log.d(TAG, "Swipe gesture completed from ($x1,$y1) to ($x2,$y2)")
                callback(true)
            }

            override fun onCancelled(gestureDescription: GestureDescription?) {
                Log.w(TAG, "Swipe gesture cancelled")
                callback(false)
            }
        }, null)
    }

    /**
     * Global Navigation Actions
     */
    fun pressHome(): Boolean = performGlobalAction(GLOBAL_ACTION_HOME)
    fun pressBack(): Boolean = performGlobalAction(GLOBAL_ACTION_BACK)
    fun pressRecents(): Boolean = performGlobalAction(GLOBAL_ACTION_RECENTS)
    fun pressNotifications(): Boolean = performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS)
    fun pressQuickSettings(): Boolean = performGlobalAction(GLOBAL_ACTION_QUICK_SETTINGS)

    fun lockScreen(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN)
        } else {
            false
        }
    }

    fun takeScreenshot(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            performGlobalAction(GLOBAL_ACTION_TAKE_SCREENSHOT)
        } else {
            false
        }
    }

    /**
     * Reads all accessible text and interactive elements in the active window hierarchy.
     * Returns a JSON string containing the hierarchy and a readable text summary.
     */
    fun readScreenHierarchy(): String {
        val root = rootInActiveWindow ?: return JSONObject().apply {
            put("error", "No active window found")
            put("summary", "")
            put("elements", JSONArray())
        }.toString()

        val elementsArray = JSONArray()
        val textCollector = StringBuilder()

        fun traverseNode(node: AccessibilityNodeInfo?) {
            if (node == null) return

            val text = node.text?.toString()?.trim()
            val desc = node.contentDescription?.toString()?.trim()
            val hasContent = !text.isNullOrEmpty() || !desc.isNullOrEmpty()

            if (hasContent || node.isClickable) {
                val rect = Rect()
                node.getBoundsInScreen(rect)

                val item = JSONObject().apply {
                    if (!text.isNullOrEmpty()) put("text", text)
                    if (!desc.isNullOrEmpty()) put("description", desc)
                    put("clickable", node.isClickable)
                    put("className", node.className?.toString() ?: "")
                    put("id", node.viewIdResourceName ?: "")
                    put("bounds", JSONArray().apply {
                        put(rect.left)
                        put(rect.top)
                        put(rect.right)
                        put(rect.bottom)
                    })
                    put("centerX", rect.centerX())
                    put("centerY", rect.centerY())
                }
                elementsArray.put(item)

                if (!text.isNullOrEmpty()) {
                    textCollector.append(text).append(" | ")
                } else if (!desc.isNullOrEmpty()) {
                    textCollector.append(desc).append(" | ")
                }
            }

            for (i in 0 until node.childCount) {
                val child = node.getChild(i)
                traverseNode(child)
            }
        }

        traverseNode(root)

        return JSONObject().apply {
            put("summary", textCollector.toString().trimEnd(' ', '|'))
            put("count", elementsArray.length())
            put("elements", elementsArray)
        }.toString()
    }

    /**
     * Finds elements matching query and performs a click either directly or by center bounds.
     */
    fun findAndClickText(query: String, callback: (Boolean) -> Unit) {
        val root = rootInActiveWindow
        if (root == null) {
            callback(false)
            return
        }

        val matches = root.findAccessibilityNodeInfosByText(query)
        if (matches.isNullOrEmpty()) {
            callback(false)
            return
        }

        for (node in matches) {
            // Direct click action
            if (node.isClickable && node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                callback(true)
                return
            }

            // Check parents for clickable action
            var parent = node.parent
            while (parent != null) {
                if (parent.isClickable && parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                    callback(true)
                    return
                }
                parent = parent.parent
            }

            // Fallback to gesture tap at node bounds center
            val rect = Rect()
            node.getBoundsInScreen(rect)
            if (rect.width() > 0 && rect.height() > 0) {
                performClick(rect.centerX().toFloat(), rect.centerY().toFloat(), callback)
                return
            }
        }

        callback(false)
    }
}
