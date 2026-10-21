<?php
header('Content-Type: application/json');
$action = $_GET['action'] ?? 'info';
if ($action === 'fatal') {
    php2shell_deliberate_test_fatal();
}
if ($action === 'session-seed' || $action === 'session-read') {
    session_start();
    if ($action === 'session-seed') {
        $_SESSION['sentinel'] = bin2hex(random_bytes(32));
    }
    echo json_encode(['sentinel' => $_SESSION['sentinel'] ?? null, 'pid' => getmypid()]);
    exit;
}
$modules = get_loaded_extensions();
sort($modules);
echo json_encode([
    'php' => PHP_VERSION,
    'sapi' => PHP_SAPI,
    'pid' => getmypid(),
    'modules' => $modules,
    'memory_limit' => ini_get('memory_limit'),
    'upload_max_filesize' => ini_get('upload_max_filesize'),
    'post_max_size' => ini_get('post_max_size'),
    'session_handler' => ini_get('session.save_handler'),
    'session_serializer' => ini_get('session.serialize_handler'),
    'file_sha256' => isset($_FILES['file']) && $_FILES['file']['error'] === UPLOAD_ERR_OK
        ? hash_file('sha256', $_FILES['file']['tmp_name']) : null,
]);
