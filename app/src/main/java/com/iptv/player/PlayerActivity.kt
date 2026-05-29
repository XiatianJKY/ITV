package com.iptv.player

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.View
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.FragmentTransaction
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.PlaybackException
import com.google.android.exoplayer2.Player
import com.google.android.exoplayer2.source.hls.HlsMediaSource
import com.google.android.exoplayer2.trackselection.DefaultTrackSelector
import com.google.android.exoplayer2.ui.PlayerView
import com.google.android.exoplayer2.upstream.DefaultHttpDataSource
import com.iptv.player.model.Channel

class PlayerActivity : AppCompatActivity() {
    
    private lateinit var playerView: PlayerView
    private lateinit var exoPlayer: ExoPlayer
    private lateinit var channelListFragment: ChannelListFragment
    private lateinit var gestureDetector: GestureDetector
    
    private lateinit var topBar: View
    private lateinit var channelNameText: TextView
    private lateinit var prevButton: ImageButton
    private lateinit var nextButton: ImageButton
    private lateinit var listButton: ImageButton
    
    private var controlsHandler = Handler(Looper.getMainLooper())
    private var isControlsVisible = true
    private var currentChannel: Channel? = null
    private var currentPosition = 0
    
    companion object {
        private const val CONTROLS_HIDE_DELAY = 3000L
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_player)
        
        initViews()
        initPlayer()
        initChannelList()
        initGestureDetector()
        setupControls()
        
        // 加载第一个频道
        if (DataManager.allChannels.isNotEmpty()) {
            currentPosition = 0
            playChannel(DataManager.allChannels[currentPosition])
        }
        
        // 3秒后隐藏控制栏
        startControlsHideTimer()
    }
    
    private fun initViews() {
        playerView = findViewById(R.id.player_view)
        topBar = findViewById(R.id.top_bar)
        channelNameText = findViewById(R.id.channel_name)
        prevButton = findViewById(R.id.btn_prev)
        nextButton = findViewById(R.id.btn_next)
        listButton = findViewById(R.id.btn_list)
    }
    
    private fun initPlayer() {
        val trackSelector = DefaultTrackSelector(this).apply {
            setParameters(buildUponParameters().setMaxVideoSize(1920, 1080))
        }
        
        exoPlayer = ExoPlayer.Builder(this)
            .setTrackSelector(trackSelector)
            .build()
        
        playerView.player = exoPlayer
        
        exoPlayer.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                when (playbackState) {
                    Player.STATE_BUFFERING -> {
                        // 缓冲中
                    }
                    Player.STATE_READY -> {
                        // 准备就绪
                    }
                    Player.STATE_ENDED -> {
                        // 播放结束，自动切换到下一个
                        nextChannel()
                    }
                }
            }
            
            override fun onPlayerError(error: PlaybackException) {
                Toast.makeText(this@PlayerActivity, "播放失败，尝试切换线路", Toast.LENGTH_SHORT).show()
                // 尝试切换到下一个频道
                nextChannel()
            }
        })
    }
    
    private fun initChannelList() {
        channelListFragment = ChannelListFragment()
        channelListFragment.setOnChannelSelectedListener { channel, position ->
            currentPosition = position
            playChannel(channel)
        }
        
        supportFragmentManager.beginTransaction()
            .add(R.id.channel_list_container, channelListFragment)
            .commit()
        
        // 初始隐藏列表
        channelListFragment.hide()
    }
    
    private fun initGestureDetector() {
        gestureDetector = GestureDetector(this, object : GestureDetector.SimpleOnGestureListener() {
            override fun onScroll(
                e1: MotionEvent?,
                e2: MotionEvent?,
                distanceX: Float,
                distanceY: Float
            ): Boolean {
                if (e1 != null && e2 != null) {
                    val diffY = e1.y - e2.y
                    if (Math.abs(diffY) > 100) {
                        if (diffY > 0) {
                            // 向上滑动 -> 上一个频道
                            previousChannel()
                        } else {
                            // 向下滑动 -> 下一个频道
                            nextChannel()
                        }
                        return true
                    }
                }
                return super.onScroll(e1, e2, distanceX, distanceY)
            }
            
            override fun onSingleTapUp(e: MotionEvent): Boolean {
                toggleControls()
                return true
            }
        })
    }
    
    private fun setupControls() {
        prevButton.setOnClickListener {
            previousChannel()
            resetControlsHideTimer()
        }
        
        nextButton.setOnClickListener {
            nextChannel()
            resetControlsHideTimer()
        }
        
        listButton.setOnClickListener {
            toggleChannelList()
            resetControlsHideTimer()
        }
    }
    
    private fun playChannel(channel: Channel) {
        currentChannel = channel
        channelNameText.text = channel.name
        
        val mediaItem = MediaItem.Builder()
            .setUri(channel.url)
            .setMimeType("application/x-mpegURL")
            .build()
        
        val dataSourceFactory = DefaultHttpDataSource.Factory()
            .setUserAgent("IPTVPlayer/1.0")
        
        val hlsMediaSource = HlsMediaSource.Factory(dataSourceFactory)
            .createMediaSource(mediaItem)
        
        exoPlayer.setMediaSource(hlsMediaSource)
        exoPlayer.prepare()
        exoPlayer.play()
        
        // 更新列表中的选中位置
        channelListFragment.updateSelectedPosition(currentPosition)
    }
    
    private fun previousChannel() {
        if (DataManager.allChannels.isEmpty()) return
        
        currentPosition--
        if (currentPosition < 0) {
            currentPosition = DataManager.allChannels.size - 1
        }
        
        playChannel(DataManager.allChannels[currentPosition])
        showControls()
        resetControlsHideTimer()
    }
    
    private fun nextChannel() {
        if (DataManager.allChannels.isEmpty()) return
        
        currentPosition++
        if (currentPosition >= DataManager.allChannels.size) {
            currentPosition = 0
        }
        
        playChannel(DataManager.allChannels[currentPosition])
        showControls()
        resetControlsHideTimer()
    }
    
    private fun toggleControls() {
        if (isControlsVisible) {
            hideControls()
        } else {
            showControls()
        }
    }
    
    private fun showControls() {
        topBar.visibility = View.VISIBLE
        isControlsVisible = true
        startControlsHideTimer()
    }
    
    private fun hideControls() {
        topBar.visibility = View.GONE
        isControlsVisible = false
        controlsHandler.removeCallbacksAndMessages(null)
    }
    
    private fun toggleChannelList() {
        if (channelListFragment.isVisible()) {
            channelListFragment.hide()
        } else {
            channelListFragment.show()
        }
    }
    
    private fun startControlsHideTimer() {
        controlsHandler.removeCallbacksAndMessages(null)
        controlsHandler.postDelayed({
            if (isControlsVisible && !channelListFragment.isVisible()) {
                hideControls()
            }
        }, CONTROLS_HIDE_DELAY)
    }
    
    private fun resetControlsHideTimer() {
        startControlsHideTimer()
    }
    
    override fun onTouchEvent(event: MotionEvent?): Boolean {
        event?.let {
            gestureDetector.onTouchEvent(it)
        }
        return super.onTouchEvent(event)
    }
    
    override fun onResume() {
        super.onResume()
        if (exoPlayer.isReleased) {
            currentChannel?.let { playChannel(it) }
        } else {
            exoPlayer.play()
        }
    }
    
    override fun onPause() {
        super.onPause()
        exoPlayer.pause()
    }
    
    override fun onDestroy() {
        super.onDestroy()
        exoPlayer.release()
        controlsHandler.removeCallbacksAndMessages(null)
    }
    
    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        return when (keyCode) {
            android.view.KeyEvent.KEYCODE_DPAD_UP -> {
                previousChannel()
                true
            }
            android.view.KeyEvent.KEYCODE_DPAD_DOWN -> {
                nextChannel()
                true
            }
            android.view.KeyEvent.KEYCODE_DPAD_CENTER, 
            android.view.KeyEvent.KEYCODE_ENTER -> {
                toggleControls()
                true
            }
            android.view.KeyEvent.KEYCODE_MENU -> {
                toggleChannelList()
                true
            }
            else -> super.onKeyDown(keyCode, event)
        }
    }
}
