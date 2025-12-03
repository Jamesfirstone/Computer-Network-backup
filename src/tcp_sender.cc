#include "tcp_sender.hh"
#include "tcp_config.hh"

using namespace std;

uint64_t TCPSender::sequence_numbers_in_flight() const
{
  // Your code here.
  return next_seqno_ - ackno_;
}

uint64_t TCPSender::consecutive_retransmissions() const
{
  // Your code here.
  return consecutive_retransmissions_;
}

void TCPSender::push( const TransmitFunction& transmit )
{
  // Your code here.
  // 有效窗口大小：零窗口视为1
  uint64_t effective_window = ( window_size_ == 0 ) ? 1 : window_size_;
  uint64_t bytes_in_flight = next_seqno_ - ackno_;
  // 确保不会下溢
  uint64_t window_available = ( bytes_in_flight < effective_window ) ? ( effective_window - bytes_in_flight ) : 0;

  // 发送尽可能多的数据
  while ( window_available > 0 && ( !input_.reader().is_finished() || !fin_sent_ ) ) {
    TCPSenderMessage msg;

    // 设置序列号
    msg.seqno = Wrap32::wrap( next_seqno_, isn_ );

    // 如果是第一次发送，需要SYN
    if ( !syn_sent_ ) {
      msg.SYN = true;
      syn_sent_ = true;
      next_seqno_++;
      window_available--;
    }

    // 读取数据（如果有窗口空间且不是SYN包）
    uint64_t payload_size = 0;
    if ( window_available > 0 && !msg.SYN && input_.reader().bytes_buffered() > 0 ) {
      payload_size = min( { window_available, TCPConfig::MAX_PAYLOAD_SIZE, input_.reader().bytes_buffered() } );
    }

    if ( payload_size > 0 ) {
      string payload = string( input_.reader().peek().substr( 0, payload_size ) );
      input_.reader().pop( payload_size );
      msg.payload = payload;
      next_seqno_ += payload_size;
      window_available -= payload_size;
    }

    // 检查是否需要发送FIN（流已结束，FIN未发送，且有窗口空间）
    if ( input_.reader().is_finished() && !fin_sent_ && window_available > 0 ) {
      msg.FIN = true;
      fin_sent_ = true;
      next_seqno_++;
      window_available--;
    }

    // 检查流是否有错误，如果有则设置RST标志
    if ( input_.has_error() ) {
      msg.RST = true;
    }

    // 只有实际有内容（SYN、数据或FIN）才发送
    if ( msg.sequence_length() > 0 ) {
      // 记录未完成报文段
      outstanding_segments_.push_back( {
        msg,
        next_seqno_ - msg.sequence_length(), // 开始序列号
        msg.sequence_length()                // 长度
      } );

      // 启动定时器（如果未运行）
      if ( !timer_running_ ) {
        timer_running_ = true;
        timer_elapsed_ms_ = 0;
      }

      // 发送报文段
      transmit( msg );
    } else {
      // 没有内容可发送，跳出循环
      break;
    }

    // 重新计算可用窗口（因为可能发送了数据）
    bytes_in_flight = next_seqno_ - ackno_;
    effective_window = ( window_size_ == 0 ) ? 1 : window_size_;
    window_available = ( bytes_in_flight < effective_window ) ? ( effective_window - bytes_in_flight ) : 0;
  }
}

TCPSenderMessage TCPSender::make_empty_message() const
{
  // Your code here.
  TCPSenderMessage msg;
  msg.seqno = Wrap32::wrap( next_seqno_, isn_ );
  // 如果输入流出现错误，设置RST标志
  if ( input_.has_error() ) {
    msg.RST = true;
  }
  return msg;
}

void TCPSender::receive( const TCPReceiverMessage& msg )
{
  // Your code here.
  // 更新窗口大小
  window_size_ = msg.window_size;

  // 如果接收到RST标志，设置错误状态
  if ( msg.RST ) {
    input_.set_error();
    // 设置错误后，可以立即停止所有活动
    // 根据实验文档，RST会重置连接，所以清理状态
    timer_running_ = false;
    consecutive_retransmissions_ = 0;
    // 注意：这里不需要清空outstanding_segments_，因为连接已经终止
    return;
  }

  // 如果有ackno，更新已确认的序列号
  if ( msg.ackno.has_value() ) {
    uint64_t new_ackno = msg.ackno->unwrap( isn_, next_seqno_ );

    // 忽略过时的ackno
    if ( new_ackno > ackno_ && new_ackno <= next_seqno_ ) {
      ackno_ = new_ackno;

      // 清理已确认的未完成报文段
      while ( !outstanding_segments_.empty() ) {
        auto& segment = outstanding_segments_.front();
        if ( segment.absolute_seqno + segment.length <= ackno_ ) {
          outstanding_segments_.pop_front();
        } else {
          break;
        }
      }

      // 重置RTO和重传计数
      current_RTO_ms_ = initial_RTO_ms_;
      consecutive_retransmissions_ = 0;

      // 如果没有未完成报文段，停止定时器
      if ( outstanding_segments_.empty() ) {
        timer_running_ = false;
      } else {
        // 重启定时器
        timer_running_ = true;
        timer_elapsed_ms_ = 0;
      }
    }
  }
}

void TCPSender::tick( uint64_t ms_since_last_tick, const TransmitFunction& transmit )
{
  // Your code here.
  if ( timer_running_ ) {
    timer_elapsed_ms_ += ms_since_last_tick;

    if ( timer_elapsed_ms_ >= current_RTO_ms_ ) {
      // 超时重传
      if ( !outstanding_segments_.empty() ) {
        transmit( outstanding_segments_.front().msg );

        // 如果窗口非零，应用指数退避
        if ( window_size_ > 0 ) {
          consecutive_retransmissions_++;
          current_RTO_ms_ *= 2;
        }

        // 重置定时器
        timer_elapsed_ms_ = 0;
      }
    }
  }
}
