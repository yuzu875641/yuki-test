<?php
// 環境変数からSupabaseのURLとAPIキーを取得
$SUPABASE_URL = getenv('SUPABASE_URL');
$SUPABASE_KEY = getenv('SUPABASE_KEY');

// REST APIを呼び出す関数
function callSupabaseApi($method, $table, $data = null, $query = '') {
    global $SUPABASE_URL, $SUPABASE_KEY;
    
    // 環境変数が設定されていない場合はエラーを返す
    if (!$SUPABASE_URL || !$SUPABASE_KEY) {
        http_response_code(500);
        die("Supabase環境変数が設定されていません。");
    }

    $url = "$SUPABASE_URL/rest/v1/$table?$query";
    $ch = curl_init($url);
    
    $headers = [
        'apikey: ' . $SUPABASE_KEY,
        'Authorization: Bearer ' . $SUPABASE_KEY,
        'Content-Type: application/json',
        'Prefer': 'return=representation'
    ];
    
    if ($method === 'POST') {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    } elseif ($method === 'PATCH') {
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PATCH');
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    } elseif ($method === 'DELETE') {
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
    }
    
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    return ['status' => $http_code, 'data' => json_decode($response, true)];
}

// ユーザーがアクセスしたURLのパスを取得
$request_uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$route_found = false;

// 投稿フォームの非同期処理（/bbs と / に関係なく動作）
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest') {
    $input_data = json_decode(file_get_contents('php://input'), true);
    
    $username = $input_data['username'] ?? '';
    $seed = $input_data['seed'] ?? '';
    $message = $input_data['message'] ?? '';
    $remember_me = $input_data['remember_me'] ?? false;

    $hashed_seed = hash('sha256', $seed);
    $user_id = substr($hashed_seed, 0, 7);

    // ユーザーが存在しない場合は新規登録
    $user_check = callSupabaseApi('GET', 'users', null, 'username=eq.' . urlencode($username));
    if (empty($user_check['data'])) {
        callSupabaseApi('POST', 'users', [
            'username' => $username, 
            'role' => 'speaker',
            'hashed_seed' => $hashed_seed
        ]);
    }

    // コマンド処理
    if (strpos($message, '/topic ') === 0) {
        $new_topic = trim(substr($message, 7));
        if (!empty($new_topic)) {
            callSupabaseApi('PATCH', 'topics', ['content' => $new_topic], 'id=eq.1');
        }
    } else if ($message === '/clear') {
        callSupabaseApi('DELETE', 'posts', null, 'delete_all=true');
    } else {
        callSupabaseApi('POST', 'posts', [
            'username' => $username, 
            'user_id' => $user_id, 
            'message' => $message
        ]);
    }
    
    $cookie_options = [
        'expires' => $remember_me ? time() + (86400 * 30) : time() - 3600,
        'path' => '/',
        'httponly' => true,
        'samesite' => 'Strict'
    ];
    setcookie('username', $username, $cookie_options);
    setcookie('seed', $seed, $cookie_options);

    $posts_data = callSupabaseApi('GET', 'posts', null, 'order=created_at.desc');
    $topic_data = callSupabaseApi('GET', 'topics');
    $current_topic = $topic_data['data'][0]['content'] ?? '今の話題';
    
    header('Content-Type: application/json');
    echo json_encode(['posts' => $posts_data['data'], 'topic' => $current_topic, 'username' => $username, 'seed' => $seed]);
    exit();
}

// ルーティング
if ($request_uri === '/' || $request_uri === '/bbs' || $request_uri === '/index.php') {
    $route_found = true;
    
    // 通常のGETリクエストでHTMLを生成
    $saved_username = $_COOKIE['username'] ?? '';
    $saved_seed = $_COOKIE['seed'] ?? '';

    $posts_data_response = callSupabaseApi('GET', 'posts', null, 'order=created_at.desc');
    $posts_data = $posts_data_response['data'] ?? [];

    $topic_data_response = callSupabaseApi('GET', 'topics');
    $topic_data = $topic_data_response['data'] ?? [];
    $current_topic = $topic_data[0]['content'] ?? '今の話題';

    $post_count = count($posts_data);

    // 投稿一覧のHTMLを動的に生成
    $posts_list_html = '';
    $display_id = $post_count;
    foreach ($posts_data as $post) {
        $utc_time = new DateTime($post['created_at']);
        $utc_time->setTimezone(new DateTimeZone('Asia/Tokyo'));
        $formatted_time = $utc_time->format('Y-m-d H:i:s');
        
        $posts_list_html .= "
            <div class='post'>
                <span class='post-meta'>No.{$display_id} |</span>
                <span class='post-meta'>{$post['username']}@{$post['user_id'] ?? ''} |</span>
                <p class='post-message'>" . nl2br(htmlspecialchars($post['message'])) . "</p>
                <small>投稿日時: {$formatted_time}</small>
            </div>
        ";
        $display_id--;
    }
    
    // テンプレートファイルの内容を読み込む
    $html_template = file_get_contents('templates/bbs.html');

    // プレースホルダーを実際のデータで置き換え
    $output_html = str_replace(
        ['{{ current_topic }}', '{{ saved_username }}', '{{ saved_seed }}', '{{ remember_me_checked }}', '{{ posts_list }}'],
        [
            htmlspecialchars($current_topic),
            htmlspecialchars($saved_username),
            htmlspecialchars($saved_seed),
            isset($_COOKIE['username']) ? 'checked' : '',
            $posts_list_html
        ],
        $html_template
    );

    echo $output_html;
}

// ルートが見つからない場合
if (!$route_found) {
    http_response_code(404);
    echo "404 Not Found";
}
