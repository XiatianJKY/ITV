package com.example.tvplayer.playback

import android.content.Context
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.exoplayer.hls.HlsMediaSource
import androidx.media3.session.MediaSession
import com.example.tvplayer.data.PlaylistParser

class PlaybackManager private constructor(context: Context) {
    val player: ExoPlayer = ExoPlayer.Builder(context)
        .setMediaSourceFactory(DefaultMediaSourceFactory(context).setLiveMinimalStartupTimeMs(1000))
        .build()
    
    private var currentChannelIndex = -1
    private val channels = PlaylistParser.getChannels()
    
    init {
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                when (playbackState) {
                    Player.STATE_ENDED -> {
                        // 播放结束时，尝试下一个
                        playNext()
                    }
                    Player.STATE_BUFFERING -> {
                        // 缓冲中，可选显示加载提示
                    }
                    Player.STATE_READY -> {
                        // 准备就绪
                    }
                }
            }
            
            override fun onPlayerError(error: PlaybackException) {
                // 播放错误时尝试切换
                playNext()
            }
        })
    }
    
    fun playChannel(index: Int) {
        if (index < 0 || index >= channels.size) return
        currentChannelIndex = index
        val channel = channels[index]
        val mediaItem = MediaItem.Builder()
            .setUri(channel.url)
            .setMediaId(channel.id.toString())
            .build()
        player.setMediaItem(mediaItem)
        player.prepare()
        player.play()
    }
    
    fun playNext() {
        if (currentChannelIndex >= 0 && currentChannelIndex + 1 < channels.size) {
            playChannel(currentChannelIndex + 1)
        } else if (currentChannelIndex >= 0 && channels.isNotEmpty()) {
            playChannel(0)  // 循环到第一个
        }
    }
    
    fun playPrevious() {
        if (currentChannelIndex > 0) {
            playChannel(currentChannelIndex - 1)
        } else if (channels.isNotEmpty()) {
            playChannel(channels.size - 1)
        }
    }
    
    fun release() {
        player.release()
    }
    
    companion object {
        @Volatile
        private var instance: PlaybackManager? = null
        
        fun getInstance(context: Context? = null): PlaybackManager {
            return instance ?: synchronized(this) {
                val ctx = context ?: throw IllegalStateException("Context required for initialization")
                instance ?: PlaybackManager(ctx.applicationContext).also { instance = it }
            }
        }
    }
}
