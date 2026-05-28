package com.iptv.player

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import com.iptv.player.databinding.FragmentChannelListBinding
import com.iptv.player.model.Channel

class ChannelListFragment : Fragment() {
    private var _binding: FragmentChannelListBinding? = null
    private val binding get() = _binding!!
    private var onChannelSelected: ((Channel) -> Unit)? = null

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentChannelListBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding.rvChannels.layoutManager = LinearLayoutManager(requireContext())
    }

    fun setChannels(channels: List<Channel>, currentChannel: Channel?) {
        val adapter = ChannelAdapter(channels) { channel ->
            onChannelSelected?.invoke(channel)
        }
        binding.rvChannels.adapter = adapter
        // 滚动到当前频道附近
        val index = channels.indexOfFirst { it.name == currentChannel?.name }
        if (index >= 0) {
            binding.rvChannels.scrollToPosition(index)
        }
    }

    fun setOnChannelSelectedListener(listener: (Channel) -> Unit) {
        onChannelSelected = listener
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
