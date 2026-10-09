export type IndustryId = 'fashion' | 'education' | 'health' | 'restaurants' | 'spa'

export type HomeCopy = {
  hero: {
    titleLine1: string
    titleLine2: string
    subtitle: string
    ctaDemo: string
    ctaTrial: string
    showcase: {
      crmTitle: string
      remarketingTitle: string
      securityTitle: string
      securityPoints: [string, string]
      chatTitle: string
      chatShop: string
      chatQuestion: string
      chatAnswer: string
      channelsTitle: string
      channels: string[]
      remarketing: {
        total: string
        viewed: string
        clicked: string
        failed: string
      }
      resultsTitle: string
      resultsHeadline: string
      remarketingPills: Array<{ label: string; isNew?: boolean }>
      newBadge: string
      menuAriaLabel: string
      chartPeriod1: string
      chartPeriod2: string
      customers: Array<{
        name: string
        phone: string
        tags: string[]
        activity?: string
        status: string
      }>
    }
  }
  platform: {
    titleLine1: string
    titleLine2: string
    features: Array<{ title: string; description: string }>
  }
  modules: {
    title: string
    badge: string
    items: Array<{
      title: string
      subtitle: string
      points: Array<{ title: string; description: string }>
    }>
  }
  industries: {
    titlePrefix: string
    titleEmphasis: string
    tabs: Record<IndustryId, string>
    tryNow: string
    items: Record<IndustryId, {
      title: string
      paragraphs: string[]
      messages: Array<{ role: 'user' | 'bot'; text: string; time?: string }>
    }>
  }
  partners: { title: string; pressTitle: string; pressSubtitle: string }
  contact: {
    title: string
    subtitle: string
    partner: string
    signup: string
    tagline: string
    nameLabel: string
    phoneLabel: string
    industryLabel: string
    submit: string
  }
  faq: { title: string; subtitle: string; items: Array<{ q: string; a: string }> }
}

export const homeContentVi: HomeCopy = {
  hero: {
    titleLine1: 'Giải pháp AI',
    titleLine2: 'bán hàng thế hệ mới',
    subtitle: 'Trợ lý AI bán hàng mạnh mẽ giúp tăng doanh số lên đến 50%',
    ctaDemo: 'Xem demo',
    ctaTrial: 'Dùng thử miễn phí',
    showcase: {
      crmTitle: 'AI Mini CRM',
      remarketingTitle: 'Remarketing AI hiệu quả',
      securityTitle: 'Bảo mật & bảo vệ dữ liệu',
      securityPoints: [
        'Mã hóa end-to-end cho mọi dữ liệu khách hàng',
        'Dữ liệu không chia sẻ và không phụ thuộc nền tảng bên thứ ba',
      ],
      chatTitle: 'AI Chatbot',
      chatShop: 'Cửa hàng thời trang',
      chatQuestion: 'Sản phẩm này còn hàng không?',
      chatAnswer: 'Còn ạ. Bạn cho shop biết chiều cao và cân nặng để shop gợi ý size phù hợp nhé.',
      channelsTitle: 'Chat đa kênh miễn phí',
      channels: ['Lazada', 'Zalo', 'Website', 'Instagram', 'Facebook', 'TikTok'],
      remarketing: {
        total: 'Tổng người nhận',
        viewed: 'Tin đã xem',
        clicked: 'Tin đã click',
        failed: 'Thất bại',
      },
      resultsTitle: 'Kết quả sau khi dùng',
      resultsHeadline: 'Tăng 50% tỷ lệ chốt đơn',
      remarketingPills: [
        { label: 'Email remarketing' },
        { label: 'SMS', isNew: true },
        { label: 'CRM tái kích hoạt khách hàng' },
      ],
      newBadge: 'Mới',
      menuAriaLabel: 'Thêm thao tác',
      chartPeriod1: 'T1',
      chartPeriod2: 'T2',
      customers: [
        {
          name: 'Truong Nguyen',
          phone: '0528234320',
          tags: ['Ticket', 'Khách mới', 'Zalo care'],
          activity: 'Đã gửi đơn',
          status: 'Hoàn tất 2 đơn hàng',
        },
        {
          name: 'Van Tran',
          phone: '0528234320',
          tags: ['Appointment', 'VIP'],
          activity: 'Khách đã thanh toán trước',
          status: 'Có lịch hẹn tư vấn',
        },
        { name: 'Trung Kien', phone: '0528234320', tags: ['Khách trung thành'], status: 'Đã mua 5 đơn gần đây' },
      ],
    },
  },
  platform: {
    titleLine1: 'Nền tảng AI',
    titleLine2: 'giúp doanh nghiệp bán nhiều hơn và tăng trưởng bền vững',
    features: [
      {
        title: 'Một nền tảng cho mọi tương tác đa kênh',
        description:
          'Tập trung hội thoại bán hàng từ Facebook, Website, Zalo, Instagram, Lazada, TikTok vào một dashboard. AI theo dõi hành trình khách hàng, không bỏ sót cơ hội.',
      },
      {
        title: 'Trợ lý AI bán hàng 24/7',
        description:
          'AI tự động tư vấn sản phẩm, giá, size và chính sách. Hiểu ngữ cảnh, ghi nhớ sở thích và chủ động dẫn dắt khách đến chốt đơn.',
      },
      {
        title: 'Remarketing AI thông minh',
        description:
          'Tự động phân loại khách và chạy chiến dịch remarketing đúng người, đúng thời điểm — tối đa hóa tỷ lệ chuyển đổi.',
      },
      {
        title: 'Thiết kế no-code & low-code hiện đại',
        description:
          'Triển khai trong vài phút với giao diện trực quan. Tùy chỉnh và mở rộng hệ thống mà không cần can thiệp kỹ thuật phức tạp.',
      },
    ],
  },
  modules: {
    title: 'Khám phá các module cốt lõi của Vismarttech AI',
    badge: 'Tăng 50% tỷ lệ chốt đơn',
    items: [
      {
        title: 'AI Chatbot thông minh',
        subtitle: 'Smart AI Chatbot',
        points: [
          { title: 'Hội thoại theo ngữ cảnh', description: 'Giữ lịch sử hội thoại, hiểu nhu cầu và gợi ý sản phẩm nhất quán.' },
          { title: 'Phản hồi tức thì', description: 'Mô phỏng tốc độ gõ tự nhiên, phản hồi 24/7 như nhân viên bán hàng.' },
          { title: 'Thu thập dữ liệu thông minh', description: 'Đồng bộ dữ liệu khách vào Mini CRM trong khi trò chuyện.' },
        ],
      },
      {
        title: 'AI Mini CRM miễn phí',
        subtitle: 'Free AI Mini CRM',
        points: [
          { title: 'Phân khúc & gắn thẻ tự động', description: 'Hồ sơ khách hàng và phân loại giúp ưu tiên lead hiệu quả.' },
          { title: 'Tích hợp hệ sinh thái AI', description: 'Kết nối Chatbot, Analytics, Content và công cụ automation.' },
        ],
      },
      {
        title: 'Giao tiếp đa kênh miễn phí',
        subtitle: 'Free omnichannel communication',
        points: [
          { title: 'Quản lý tin nhắn một nơi', description: 'Facebook, Zalo, TikTok, Instagram, Lazada và website trong một giao diện.' },
          { title: 'Luồng hội thoại liền mạch', description: 'Bot và nhân viên cùng xử lý một cuộc trò chuyện.' },
          { title: 'Phân công tự động', description: 'Định tuyến hội thoại theo workflow và agent phù hợp.' },
        ],
      },
    ],
  },
  industries: {
    titlePrefix: 'Giải pháp AI bán hàng',
    titleEmphasis: 'tối ưu cho mọi ngành',
    tabs: {
      fashion: 'THỜI TRANG',
      education: 'GIÁO DỤC',
      health: 'Y TẾ & PHÒNG KHÁM',
      restaurants: 'NHÀ HÀNG',
      spa: 'SPA & MỸ PHẨM',
    },
    tryNow: 'Dùng thử ngay',
    items: {
      fashion: {
        title: 'THỜI TRANG',
        paragraphs: [
          'AI Chatbot không chỉ tư vấn bằng text — nó hiểu sản phẩm qua hình ảnh, giúp khách chọn đúng size và màu sắc nhanh hơn.',
          'Bằng cách thu thập chiều cao, cân nặng và sở thích, AI gợi ý size chính xác, giảm tỷ lệ đổi trả và tăng tốc chốt đơn.',
        ],
        messages: [
          { role: 'user', text: 'Shop ơi, áo khoác trên fanpage còn hàng không?', time: '16:46' },
          { role: 'bot', text: 'Dạ còn ạ. Bạn cho shop biết chiều cao và cân nặng để gợi ý size phù hợp nhé.', time: '16:46' },
          { role: 'user', text: 'Mình cao 165cm, nặng 58kg thì mặc size nào?', time: '16:47' },
          { role: 'bot', text: 'Theo số đo của bạn, shop gợi ý size M — vừa vặn và thoải mái khi mặc.', time: '16:48' },
        ],
      },
      education: {
        title: 'GIÁO DỤC',
        paragraphs: [
          'AI Chatbot thu thập trình độ, mục tiêu học và lịch rảnh của học viên để gợi ý khóa học phù hợp ngay trong cuộc trò chuyện.',
          'Tự động trả lời lịch khai giảng, học phí và điều kiện đầu vào — giảm tải cho tư vấn viên và tăng tỷ lệ đăng ký.',
        ],
        messages: [
          { role: 'user', text: 'Chào trung tâm, mình muốn tìm lớp thiết kế đồ họa. Có lịch buổi tối không?', time: '11:00' },
          { role: 'bot', text: 'Bạn đang ở khu vực nào để trung tâm gửi lịch phù hợp nhé?', time: '11:00' },
          { role: 'user', text: 'Mình ở Quận 1. Có lớp nào học thứ 3 và thứ 5 không?', time: '11:02' },
          { role: 'bot', text: 'Dạ có lớp thứ 3 và thứ 5, từ 19:30–21:30. Bạn muốn đăng ký buổi học thử không?', time: '11:04' },
        ],
      },
      health: {
        title: 'Y TẾ & PHÒNG KHÁM',
        paragraphs: [
          'AI Chatbot xác định nhu cầu ban đầu từ triệu chứng và hướng dẫn khách chọn dịch vụ phù hợp trước khi đến phòng khám.',
          'Hỗ trợ đặt lịch khám, nhắc lịch tái khám và trả lời câu hỏi thường gặp — giảm quá tải cho lễ tân và tăng trải nghiệm bệnh nhân.',
        ],
        messages: [
          { role: 'user', text: 'Phòng khám có khám răng tổng quát không ạ?', time: '09:10' },
          { role: 'bot', text: 'Dạ có ạ. Phòng khám cung cấp khám tổng quát và tư vấn ban đầu miễn phí.', time: '09:10' },
          { role: 'user', text: 'Răng mình hay ê buốt khi uống lạnh, cần điều trị gì?', time: '09:12' },
          { role: 'bot', text: 'Tùy mức độ, bác sĩ có thể trám răng, trám ê buốt hoặc điều trị sâu răng. Bạn đặt lịch khám sớm nhất lúc 14:00 hôm nay nhé.', time: '09:14' },
        ],
      },
      restaurants: {
        title: 'NHÀ HÀNG',
        paragraphs: [
          'AI Chatbot hỗ trợ đặt bàn theo giờ, số khách và khu vực ngồi — phản hồi tức thì trên mọi kênh chat.',
          'Gợi ý món theo sở thích, thông báo khuyến mãi và xác nhận đặt bàn tự động — giúp nhân viên tập trung phục vụ tại chỗ.',
        ],
        messages: [
          { role: 'user', text: 'Tối nay nhà hàng còn bàn trống không ạ?', time: '18:45' },
          { role: 'bot', text: 'Dạ còn bàn cho tối nay. Bạn đi mấy người và muốn ngồi khu vực nào?', time: '18:45' },
          { role: 'user', text: '4 người, khu trong nhà. Khoảng 7 giờ được không?', time: '18:47' },
          { role: 'bot', text: '7 giờ tối vẫn còn chỗ khu trong nhà — mình giữ bàn cho 4 người nhé.', time: '18:48' },
        ],
      },
      spa: {
        title: 'SPA & MỸ PHẨM',
        paragraphs: [
          'AI Chatbot đánh giá tình trạng da qua mô tả của khách và gợi ý liệu trình spa phù hợp.',
          'Tư vấn sản phẩm chăm sóc, đặt lịch hẹn và nhắc lịch tái khám — tăng doanh thu dịch vụ và sản phẩm mỹ phẩm.',
        ],
        messages: [
          { role: 'user', text: 'Mình bị mụn ẩn và thâm, spa có liệu trình phù hợp không?', time: '10:10' },
          { role: 'bot', text: 'Dạ có liệu trình chuyên sâu làm sạch và cải thiện sắc tố da cho mụn ẩn.', time: '10:10' },
          { role: 'user', text: 'Mất bao lâu thì thấy cải thiện?', time: '10:12' },
          { role: 'bot', text: 'Thường 4–6 buổi tùy tình trạng da hiện tại. Bạn muốn đặt lịch tư vấn miễn phí tuần này không?', time: '10:14' },
        ],
      },
    },
  },
  partners: {
    title: 'Đối tác cùng các nền tảng hàng đầu',
    pressTitle: 'Báo chí nói gì về chúng tôi',
    pressSubtitle: 'Đánh giá từ các đơn vị truyền thông uy tín',
  },
  contact: {
    title: 'Liên hệ Vismarttech ngay hôm nay',
    subtitle: 'Nhận tư vấn AI chuyên sâu để tối ưu tương tác khách hàng và tăng trưởng doanh nghiệp',
    partner: 'Đối tác',
    signup: 'Đăng ký',
    tagline: 'Tối ưu bán hàng, tự động hóa vận hành và chuyển đổi số cho SME',
    nameLabel: 'Họ và tên *',
    phoneLabel: 'Số điện thoại *',
    industryLabel: 'Ngành nghề *',
    submit: 'Nhận tư vấn',
  },
  faq: {
    title: 'Câu hỏi thường gặp',
    subtitle: 'Giải đáp nhanh để bạn sử dụng hiệu quả hơn',
    items: [
      {
        q: 'Vismarttech tích hợp được những nền tảng nào?',
        a: 'Facebook, Zalo OA, TikTok Business, Instagram, Lazada và Website — tập trung dữ liệu khách hàng và tăng tỷ lệ chuyển đổi.',
      },
      {
        q: 'Mất bao lâu để tích hợp chatbot hoạt động đầy đủ?',
        a: 'Thông thường 2–4 tuần cho pilot, tùy dữ liệu và số lượng tích hợp bên thứ ba.',
      },
      {
        q: 'Bảng giá phù hợp doanh nghiệp nhỏ không?',
        a: 'Có gói Sandbox và Professional linh hoạt — xem trang Bảng giá hoặc liên hệ sales.',
      },
      {
        q: 'Xử lý ngôn ngữ phức tạp (viết tắt, lỗi chính tả) thế nào?',
        a: 'Mô hình LLM và RAG được tinh chỉnh theo ngành, hiểu ngữ cảnh hội thoại thực tế.',
      },
      {
        q: 'Bảo mật dữ liệu khách hàng ra sao?',
        a: 'Phân quyền workspace, mã hóa truyền tải và tùy chọn triển khai self-hosted theo yêu cầu.',
      },
      {
        q: 'Có cần đội kỹ thuật nội bộ vận hành không?',
        a: 'Không bắt buộc. Giao diện no-code giúp team vận hành tự cấu hình workflow và kênh.',
      },
    ],
  },
}

export const homeContentEn: HomeCopy = {
  hero: {
    titleLine1: 'Next-Generation AI',
    titleLine2: 'Sales Solutions',
    subtitle: 'Powerful AI Sales Assistant that boosts your sales by up to 50%',
    ctaDemo: 'Demo',
    ctaTrial: 'Free trial',
    showcase: {
      crmTitle: 'AI Mini CRM',
      remarketingTitle: 'Effective AI remarketing',
      securityTitle: 'Security & data protection',
      securityPoints: [
        'End-to-end encryption for all customer data',
        'Data is not shared and does not depend on third-party platforms',
      ],
      chatTitle: 'AI Chatbot',
      chatShop: 'Fashion shop',
      chatQuestion: 'Is this item still in stock?',
      chatAnswer: 'Yes, it is. Please share your height and weight so we can recommend the right size.',
      channelsTitle: 'Free multi-channel chat',
      channels: ['Lazada', 'Zalo', 'Website', 'Instagram', 'Facebook', 'TikTok'],
      remarketing: {
        total: 'Total recipients',
        viewed: 'Messages viewed',
        clicked: 'Messages clicked',
        failed: 'Failed',
      },
      resultsTitle: 'Results after using',
      resultsHeadline: 'Boost closing rate by up to 50%',
      remarketingPills: [
        { label: 'Email remarketing' },
        { label: 'SMS', isNew: true },
        { label: 'CRM customer re-engagement' },
      ],
      newBadge: 'New',
      menuAriaLabel: 'More options',
      chartPeriod1: 'T1',
      chartPeriod2: 'T2',
      customers: [
        {
          name: 'Truong Nguyen',
          phone: '0528234320',
          tags: ['Ticket', 'New customer', 'Zalo care'],
          activity: 'Order sent',
          status: 'Completed 2 orders',
        },
        {
          name: 'Van Tran',
          phone: '0528234320',
          tags: ['Appointment', 'VIP'],
          activity: 'Customer paid in advance',
          status: 'Consultation appointment scheduled',
        },
        { name: 'Trung Kien', phone: '0528234320', tags: ['Loyal customer'], status: 'Purchased 5 recent orders' },
      ],
    },
  },
  platform: {
    titleLine1: 'The AI Platform',
    titleLine2: 'that empowers businesses to sell more and achieve sustainable growth',
    features: [
      {
        title: 'A single platform for all multi-channel customer interactions',
        description:
          'Centralize sales conversations from Facebook, Website, Zalo, Instagram, Lazada, TikTok and more. AI tracks each customer journey so no opportunity is missed.',
      },
      {
        title: '24/7 automated AI sales assistant',
        description:
          'AI recommends products and handles pricing, sizing, and policies. Understands context, remembers preferences, and guides customers toward conversion.',
      },
      {
        title: 'Intelligent AI-powered remarketing',
        description:
          'Automatically categorizes customers and runs smart remarketing campaigns at the right time to maximize conversion rates.',
      },
      {
        title: 'Modern no-code & low-code design',
        description:
          'Get started in minutes with an intuitive interface. Customize and scale without complex technical intervention.',
      },
    ],
  },
  modules: {
    title: 'Explore the core modules of Vismarttech AI',
    badge: 'Boost sales by up to 50%',
    items: [
      {
        title: 'Smart AI Chatbot',
        subtitle: 'Smart AI Chatbot',
        points: [
          { title: 'Context-Aware Conversations', description: 'Retains conversation history and delivers consistent product recommendations.' },
          { title: 'Instant responses', description: 'Natural typing speed simulation with 24/7 instant replies.' },
          { title: 'Intelligent data collection', description: 'Syncs customer data into Mini CRM during conversations.' },
        ],
      },
      {
        title: 'Free AI Mini CRM',
        subtitle: 'Free AI Mini CRM',
        points: [
          { title: 'Smart Customer Profiling & Segmentation', description: 'Automatic tagging and segmentation to prioritize leads effectively.' },
          { title: 'Built for advanced AI ecosystems', description: 'Integrates with Chatbot, Analytics, Content, and automation tools.' },
        ],
      },
      {
        title: 'Free omnichannel communication',
        subtitle: 'Free omnichannel communication',
        points: [
          { title: 'Manage all messages in one place', description: 'Facebook, Zalo, TikTok, Instagram, Lazada, and your website in one interface.' },
          { title: 'Seamless conversation flow', description: 'Bots and human agents collaborate in the same thread.' },
          { title: 'Automated assignment', description: 'Routes conversations to the right team or agent by workflow.' },
        ],
      },
    ],
  },
  industries: {
    titlePrefix: "Vismarttech's AI sales solution is",
    titleEmphasis: 'optimized for every industry',
    tabs: {
      fashion: 'FASHION',
      education: 'EDUCATION',
      health: 'HEALTH & CLINIC',
      restaurants: 'RESTAURANTS',
      spa: 'SPA & COSMETICS',
    },
    tryNow: 'Try now',
    items: {
      fashion: {
        title: 'FASHION',
        paragraphs: [
          'AI Chatbots go beyond text — they understand products from images and help customers pick the right size and color faster.',
          'By collecting height, weight, and preferences, AI recommends accurate sizing, reducing returns and speeding up checkout.',
        ],
        messages: [
          { role: 'user', text: 'Hi shop, is the jacket on your page still available?', time: '16:46' },
          { role: 'bot', text: 'Yes, it is in stock. Share your height and weight so we can recommend the right size.', time: '16:46' },
          { role: 'user', text: "I'm 165cm and 58kg. Which size fits best?", time: '16:47' },
          { role: 'bot', text: 'Based on your measurements, we recommend size M for a comfortable fit.', time: '16:48' },
        ],
      },
      education: {
        title: 'EDUCATION',
        paragraphs: [
          'AI Chatbots collect learner level, goals, and availability to recommend the right course during the conversation.',
          'Automatically answers schedules, tuition, and entry requirements — reducing counselor workload and boosting enrollments.',
        ],
        messages: [
          { role: 'user', text: "Hello, I'm looking for a graphic design class. Do you have an evening schedule?", time: '11:00' },
          { role: 'bot', text: 'Which area are you in? Let us know so we can share a schedule that fits.', time: '11:00' },
          { role: 'user', text: "I'm in District 1. Are there classes on Tue and Thu?", time: '11:02' },
          { role: 'bot', text: 'Yes, we have a class on Tue and Thu from 7:30–9:30 PM. Would you like a trial session?', time: '11:04' },
        ],
      },
      health: {
        title: 'HEALTH & CLINIC',
        paragraphs: [
          'AI Chatbots identify initial needs from symptoms and guide patients to the right services before visiting the clinic.',
          'Supports appointment booking, follow-up reminders, and FAQs — reducing front-desk load and improving patient experience.',
        ],
        messages: [
          { role: 'user', text: 'Do you offer general dental check-ups?', time: '09:10' },
          { role: 'bot', text: 'Yes, we provide general check-ups and free initial consultations.', time: '09:10' },
          { role: 'user', text: 'My teeth are sensitive to cold drinks. What treatment do I need?', time: '09:12' },
          { role: 'bot', text: 'Depending on severity, treatment may include desensitizing, fillings, or cavity care. We have an opening at 2:00 PM today.', time: '09:14' },
        ],
      },
      restaurants: {
        title: 'RESTAURANTS',
        paragraphs: [
          'AI Chatbots handle table reservations by time, party size, and seating area — with instant replies on every chat channel.',
          'Suggests dishes by preference, shares promotions, and confirms bookings automatically so staff can focus on in-house service.',
        ],
        messages: [
          { role: 'user', text: 'Hello, are there tables available tonight?', time: '18:45' },
          { role: 'bot', text: 'Yes, we have availability tonight. How many guests and which seating area do you prefer?', time: '18:45' },
          { role: 'user', text: 'Four people, indoor seating. Around 7 PM works?', time: '18:47' },
          { role: 'bot', text: 'We still have indoor seating at 7:00 PM — I can reserve a table for four.', time: '18:48' },
        ],
      },
      spa: {
        title: 'SPA & COSMETICS',
        paragraphs: [
          'AI Chatbots assess skin concerns from customer descriptions and recommend suitable spa treatments.',
          'Advises on skincare products, books appointments, and sends reminders — boosting service and cosmetics revenue.',
        ],
        messages: [
          { role: 'user', text: 'I have closed comedones and dark spots. Do you have a treatment plan?', time: '10:10' },
          { role: 'bot', text: 'Yes, we offer intensive plans to cleanse skin and improve tone for comedonal acne.', time: '10:10' },
          { role: 'user', text: 'How long until I see improvement?', time: '10:12' },
          { role: 'bot', text: 'Typically 4–6 sessions depending on your skin condition. Would you like a free consultation this week?', time: '10:14' },
        ],
      },
    },
  },
  partners: {
    title: 'We partner with leading platforms',
    pressTitle: 'What the press says about us',
    pressSubtitle: 'Insights and evaluations from trusted media outlets',
  },
  contact: {
    title: 'Contact Vismarttech today',
    subtitle: 'Get expert AI consulting to optimize customer interactions and accelerate business growth',
    partner: 'Partner',
    signup: 'Signup',
    tagline: 'Optimize sales, automate operations, and drive digital transformation for SMEs',
    nameLabel: 'First & last name *',
    phoneLabel: 'Phone number *',
    industryLabel: 'Your Industry *',
    submit: 'Get consultation',
  },
  faq: {
    title: 'Frequently Asked Questions',
    subtitle: 'Quick answers to help you use the platform more effectively',
    items: [
      {
        q: 'Which platforms can Vismarttech integrate with?',
        a: 'Facebook, Zalo OA, TikTok Business, Instagram, Lazada, and Websites — centralizing customer data to increase conversion rates.',
      },
      {
        q: 'How long does it take to integrate a fully functional chatbot?',
        a: 'Typically 2–4 weeks for a pilot, depending on data readiness and third-party integrations.',
      },
      {
        q: 'Are there plans suitable for small businesses?',
        a: 'Yes — see our Pricing page for Sandbox and Professional tiers, or contact sales.',
      },
      {
        q: 'How do you handle unclear language (abbreviations, typos)?',
        a: 'LLM and RAG tuned per industry understand real conversation context.',
      },
      {
        q: 'How is data security ensured?',
        a: 'Workspace permissions, encrypted transport, and optional self-hosted deployment.',
      },
      {
        q: 'Do we need an in-house technical team?',
        a: 'Not required — no-code tooling lets operations teams configure workflows and channels.',
      },
    ],
  },
}
