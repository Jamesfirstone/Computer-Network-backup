#include "tcp_receiver.hh"
#include "wrapping_integers.hh"

using namespace std;

void TCPReceiver::receive( TCPSenderMessage message )
{
  // Your code here.
  // 如果设置了RST标志，重置流
  if ( message.RST ) {
    // 通过reader()来设置错误，因为reader()返回非const引用
    reassembler_.reader().set_error();
    return;
  }

  // 如果设置了SYN标志，设置初始序列号
  if ( message.SYN ) {
    isn_ = message.seqno;
    syn_received_ = true;
  }

  // 如果没有收到SYN，忽略所有数据
  if ( !syn_received_ ) {
    return;
  }

  // 计算数据的起始绝对序列号
  // 使用writer().bytes_pushed()作为checkpoint，因为这是下一个期望的流索引
  uint64_t checkpoint = reassembler_.writer().bytes_pushed();
  uint64_t absolute_seqno = message.seqno.unwrap( *isn_, checkpoint );

  // 计算流索引：绝对序列号减1，因为SYN占用一个序列号但不属于数据流
  uint64_t stream_index = absolute_seqno;
  if ( message.SYN ) {
    // SYN标志本身占用一个序列号，所以数据从下一个序列号开始
    stream_index = 0; // 第一个数据字节的流索引是0
  } else {
    // 对于非SYN段，减去SYN占用的序列号
    stream_index = absolute_seqno - 1;
  }

  // 将数据插入到重组器中
  reassembler_.insert( stream_index, message.payload, message.FIN );
}

TCPReceiverMessage TCPReceiver::send() const
{
  // Your code here.
  TCPReceiverMessage msg;

  // 如果已经收到SYN，计算ackno
  if ( syn_received_ ) {
    // 下一个期望的序列号 = 已组装的字节数 + 1 (考虑SYN) + (如果流已结束，考虑FIN)
    uint64_t absolute_ackno = reassembler_.writer().bytes_pushed() + 1; // +1 for SYN

    // 如果流已经结束并且所有字节都已组装，加上FIN
    if ( reassembler_.writer().is_closed() ) {
      absolute_ackno++; // +1 for FIN
    }

    msg.ackno = Wrap32::wrap( absolute_ackno, *isn_ );
  }

  // 设置窗口大小
  uint64_t available_cap = reassembler_.writer().available_capacity();
  msg.window_size = available_cap > UINT16_MAX ? UINT16_MAX : static_cast<uint16_t>( available_cap );

  // 检查是否应该设置RST标志
  msg.RST = reassembler_.writer().has_error();

  return msg;
}
