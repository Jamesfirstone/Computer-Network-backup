#pragma once

#include "byte_stream.hh"
#include "tcp_receiver_message.hh"
#include "tcp_sender_message.hh"

#include <cstdint>
#include <functional>
#include <list>
#include <memory>
#include <optional>
#include <queue>

class TCPSender
{
public:
  /* Construct TCP sender with given default Retransmission Timeout and possible ISN */
  TCPSender( ByteStream&& input, Wrap32 isn, uint64_t initial_RTO_ms )
    : input_( std::move( input ) )
    , isn_( isn )
    , initial_RTO_ms_( initial_RTO_ms )
    , next_seqno_( 0 )
    , ackno_( 0 )
    , window_size_( 1 )          // 根据FAQ，初始窗口大小为1
    , current_RTO_ms_( initial_RTO_ms )
    , timer_elapsed_ms_( 0 )
    , timer_running_( false )
    , consecutive_retransmissions_( 0 )
    , outstanding_segments_()  // 添加这一行
    , syn_sent_( false )
    , fin_sent_( false )
  {}

  /* Generate an empty TCPSenderMessage */
  TCPSenderMessage make_empty_message() const;

  /* Receive and process a TCPReceiverMessage from the peer's receiver */
  void receive( const TCPReceiverMessage& msg );

  /* Type of the `transmit` function that the push and tick methods can use to send messages */
  using TransmitFunction = std::function<void( const TCPSenderMessage& )>;

  /* Push bytes from the outbound stream */
  void push( const TransmitFunction& transmit );

  /* Time has passed by the given # of milliseconds since the last time the tick() method was called */
  void tick( uint64_t ms_since_last_tick, const TransmitFunction& transmit );

  // Accessors
  uint64_t sequence_numbers_in_flight() const;  // How many sequence numbers are outstanding?
  uint64_t consecutive_retransmissions() const; // How many consecutive *re*transmissions have happened?
  Writer& writer() { return input_.writer(); }
  const Writer& writer() const { return input_.writer(); }

  // Access input stream reader, but const-only (can't read from outside)
  const Reader& reader() const { return input_.reader(); }

private:
  // Variables initialized in constructor
  ByteStream input_;
  Wrap32 isn_;
  uint64_t initial_RTO_ms_;

  // 需要添加的成员变量
  uint64_t next_seqno_;  // 下一个要发送的序列号（绝对）
  uint64_t ackno_;       // 已确认的序列号（绝对）
  uint64_t window_size_; // 接收方窗口大小

  // 重传相关
  uint64_t current_RTO_ms_;              // 当前RTO值
  uint64_t timer_elapsed_ms_;            // 定时器已运行时间
  bool timer_running_;                   // 定时器是否在运行
  uint64_t consecutive_retransmissions_; // 连续重传次数

  // 未完成的报文段
  struct OutstandingSegment
  {
    TCPSenderMessage msg;
    uint64_t absolute_seqno; // 绝对序列号
    uint64_t length;         // 报文段长度
  };
  std::deque<OutstandingSegment> outstanding_segments_;

  // 状态标志
  bool syn_sent_; // SYN是否已发送
  bool fin_sent_; // FIN是否已发送
};
