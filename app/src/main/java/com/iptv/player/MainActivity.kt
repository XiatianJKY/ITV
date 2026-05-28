package com.iptv.player

import android.content.pm.ActivityInfo
import android.content.res.Configuration
import android.os.Bundle
import android.util.Log
import android.view.View
import android.view.WindowManager
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.SimpleExoPlayer
import com.google.android.exoplayer2.source.hls.HlsMediaSource
import com.google.android.exoplayer2.trackselection.DefaultTrackSelector
import com.google.android.exoplayer2.ui.PlayerView
import com.google.android.exoplayer2.upstream.DefaultHttpDataSource
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var playerView: PlayerView
    private lateinit var channelList: RecyclerView
    private lateinit var currentChannelName: TextView
    private lateinit var channelCount: TextView
    private lateinit var fullscreenButton: ImageButton
    private var exoPlayer: SimpleExoPlayer? = null
    private var currentChannelUrl: String? = null
    private var isFullscreen = false
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        playerView = findViewById(R.id.player_view)
        channelList = findViewById(R.id.channel_list)
        currentChannelName = findViewById(R.id.current_channel_name)
        channelCount = findViewById(R.id.channel_count)
        fullscreenButton = findViewById(R.id.fullscreen_button)

        channelList.layoutManager = LinearLayoutManager(this)

        fullscreenButton.setOnClickListener { toggleFullscreen() }

        val baseUrl = BuildConfig.BASE_URL
        val normalizedBase = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        val m3uUrl = "${normalizedBase}tv.m3u"
        val txtUrl = "${normalizedBase}tv.txt"

        loadPlaylist(m3uUrl, true) { success ->
            if (!success) {
                loadPlaylist(txtUrl, false) { txtSuccess ->
                    if (!txtSuccess) {
                        runOnUiThread {
                            Toast.makeText(this, "无法加载播放列表\n请检查网络或源地址", Toast.LENGTH_LONG).show()
                        }
                    }
                }
            }
        }
    }

    private fun loadPlaylist(url: String, isM3u: Boolean, callback: (Boolean) -> Unit) {
        Thread {
            try {
                val request = Request.Builder().url(url).build()
                val response = client.newCall(request).execute()
                if (!response.isSuccessful) {
                    callback(false)
                    return@Thread
                }
                val content = response.body?.string() ?: ""
                val channels = if (isM3u) parseM3u(content) else parseTxt(content)
                runOnUiThread {
                    if (channels.isEmpty()) {
                        Toast.makeText(this, "未找到任何频道", Toast.LENGTH_SHORT).show()
                        callback(false)
                    } else {
                        setupChannelList(channels)
                        channelCount.text = "${channels.size}个频道"
                        playChannel(channels[0].url, channels[0].name)
                        callback(true)
                    }
                }
            } catch (e: Exception) {
                Log.e("IPTVPlayer", "加载失败", e)
                callback(false)
            }
        }.start()
    }

    private fun parseM3u(content: String): List<Channel> {
        val channels = mutableListOf<Channel>()
        var currentName = ""
        content.lines().forEach { line ->
            val trimmed = line.trim()
            when {
                trimmed.startsWith("#EXTINF") -> {
                    val idx = trimmed.lastIndexOf(",")
                    if (idx != -1) currentName = trimmed.substring(idx + 1).trim()
                }
                trimmed.startsWith("http") && currentName.isNotEmpty() -> {
                    channels.add(Channel(currentName, trimmed))
                    currentName = ""
                }
            }
        }
        return channels
    }

    private fun parseTxt(content: String): List<Channel> {
        val channels = mutableListOf<Channel>()
        content.lines().forEach { line ->
            val trimmed = line.trim()
            if (trimmed.isNotEmpty() && !trimmed.startsWith("#")) {
                val comma = trimmed.indexOf(',')
                if (comma > 0) {
                    val name = trimmed.substring(0, comma)
                    val url = trimmed.substring(comma + 1)
                    if (url.startsWith("http")) {
                        channels.add(Channel(name, url))
                    }
                }
            }
        }
        return channels
    }

    private fun setupChannelList(channels: List<Channel>) {
        val adapter = ChannelAdapter(channels) { channel, position ->
            playChannel(channel.url, channel.name)
            (channelList.adapter as? ChannelAdapter)?.setSelectedPosition(position)
        }
        channelList.adapter = adapter
    }

    private fun playChannel(url: String, name: String) {
        if (currentChannelUrl == url && exoPlayer?.isPlaying == true) return
        currentChannelUrl = url
        currentChannelName.text = "▶ $name"

        releasePlayer()
        val trackSelector = DefaultTrackSelector(this)
        exoPlayer = SimpleExoPlayer.Builder(this).setTrackSelector(trackSelector).build()
        playerView.player = exoPlayer

        val dataSourceFactory = DefaultHttpDataSource.Factory()
        val mediaSource = HlsMediaSource.Factory(dataSourceFactory)
            .createMediaSource(MediaItem.fromUri(url))
        exoPlayer?.setMediaSource(mediaSource)
        exoPlayer?.prepare()
        exoPlayer?.playWhenReady = true
    }

    private fun releasePlayer() {
        exoPlayer?.release()
        exoPlayer = null
        playerView.player = null
    }

    private fun toggleFullscreen() {
        if (isFullscreen) {
            supportActionBar?.show()
            window.clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN)
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_VISIBLE
            requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
            fullscreenButton.setImageResource(R.drawable.ic_fullscreen)
            isFullscreen = false
        } else {
            supportActionBar?.hide()
            window.setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN
            )
            window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            )
            requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            fullscreenButton.setImageResource(R.drawable.ic_fullscreen_exit)
            isFullscreen = true
        }
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        if (newConfig.orientation == Configuration.ORIENTATION_LANDSCAPE) {
            supportActionBar?.hide()
        } else {
            supportActionBar?.show()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        releasePlayer()
    }

    data class Channel(val name: String, val url: String)
}
